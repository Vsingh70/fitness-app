"""Structured meal plans: nested CRUD, totals roll-up, calendar resolution.

Plan shapes (``plan_kind``):
- ``daily_repeating``: one ``every_day`` template applies to every date.
- ``training_rest``: ``training`` / ``rest`` templates. When ``synced_to_program``
  a date is a training day if the user has a ScheduledWorkout on it; otherwise
  manual mapping via ``training_dows`` (weekday ints, 0=Monday).
- ``weekly``: a ``dow_<weekday>`` template per weekday. With ``week_resets`` the
  plan is flagged ``needs_week_review`` on read once the week has rolled over.

Totals: an item carries denormalized macros at its chosen amount (food per-100g
* grams/100). A meal totals its items; a day template totals its meals. When
``content_mode`` includes meals and a day has no explicit per-day target, the
day's effective targets = the summed meal totals.

Amount -> grams:
- ``g``: as-is.
- ``ml``: treated as grams (1 ml == 1 g, water-equivalent; documented).
- ``serving``: ``food_servings.grams`` (the gram weight of one serving) * amount.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    MealPlanContentMode,
    MealPlanDayRole,
    MealPlanItemUnit,
    MealPlanKind,
)
from app.models.food import Food, FoodServing
from app.models.meal_plan import MealPlan, MealPlanDay, MealPlanItem, MealPlanMeal
from app.models.scheduled_workout import ScheduledWorkout
from app.models.user import User

_ZERO = Decimal("0")
_Q = Decimal("0.01")

_MACRO_ATTRS = ("kcal", "protein_g", "carbs_g", "fat_g")
_PER_100G = {
    "kcal": "kcal_per_100g",
    "protein_g": "protein_g_per_100g",
    "carbs_g": "carbs_g_per_100g",
    "fat_g": "fat_g_per_100g",
}


def _now() -> datetime:
    return datetime.now(tz=UTC)


# ---------------------------------------------------------------------------
# Amount -> grams + macro denormalization
# ---------------------------------------------------------------------------


def resolve_grams(
    *, amount: Decimal, unit: MealPlanItemUnit, serving: FoodServing | None
) -> Decimal:
    """Resolve an (amount, unit, serving) tuple to canonical grams.

    Shared by meal plans (``meal_plan_items``) and meal logging (``meal_items``)
    so the two stay in lockstep.
    """
    if unit in (MealPlanItemUnit.g, MealPlanItemUnit.ml):
        # ml is water-equivalent: 1 ml == 1 g.
        return amount
    # serving: one serving's gram weight * amount.
    if serving is None or serving.grams is None:
        raise HTTPException(
            status_code=422,
            detail="A serving with a known gram weight is required for unit 'serving'.",
        )
    return (amount * serving.grams).quantize(_Q)


def macros_for_grams(food: Food, grams: Decimal) -> dict[str, Decimal | None]:
    """Denormalize a food's per-100g macros to the given grams (kcal + macros)."""
    out: dict[str, Decimal | None] = {}
    for target in _MACRO_ATTRS:
        per_100g = getattr(food, _PER_100G[target])
        out[target] = None if per_100g is None else (per_100g * grams / Decimal("100")).quantize(_Q)
    return out


async def load_food(session: AsyncSession, user: User, food_id: UUID) -> Food:
    food = (await session.execute(select(Food).where(Food.id == food_id))).scalar_one_or_none()
    if food is None or (food.owner_id is not None and food.owner_id != user.id):
        raise HTTPException(status_code=404, detail="Food not found.")
    return food


async def load_serving(session: AsyncSession, food_id: UUID, serving_id: UUID) -> FoodServing:
    serving = (
        await session.execute(
            select(FoodServing).where(FoodServing.id == serving_id, FoodServing.food_id == food_id)
        )
    ).scalar_one_or_none()
    if serving is None:
        raise HTTPException(status_code=404, detail="Serving not found for that food.")
    return serving


async def resolve_item_grams_and_macros(
    session: AsyncSession,
    user: User,
    *,
    food_id: UUID,
    amount: Decimal,
    unit: MealPlanItemUnit,
    serving_id: UUID | None,
) -> tuple[Decimal, dict[str, Decimal | None]]:
    """Validate (amount, unit, serving) for a food and return (grams, macros).

    Centralizes the amount->grams + denormalization rules + unit/serving
    validation so both ``meal_plan_items`` and ``meal_items`` resolve identically.
    """
    if amount <= 0:
        raise HTTPException(status_code=422, detail="amount must be > 0")
    food = await load_food(session, user, food_id)
    serving: FoodServing | None = None
    if unit == MealPlanItemUnit.serving:
        if serving_id is None:
            raise HTTPException(status_code=422, detail="serving_id required for unit 'serving'.")
        serving = await load_serving(session, food_id, serving_id)
    elif serving_id is not None:
        raise HTTPException(status_code=422, detail="serving_id only valid when unit is 'serving'.")
    grams = resolve_grams(amount=amount, unit=unit, serving=serving)
    return grams, macros_for_grams(food, grams)


async def _build_item(
    session: AsyncSession,
    user: User,
    *,
    food_id: UUID,
    amount: Decimal,
    unit: MealPlanItemUnit,
    serving_id: UUID | None,
) -> MealPlanItem:
    grams, macros = await resolve_item_grams_and_macros(
        session, user, food_id=food_id, amount=amount, unit=unit, serving_id=serving_id
    )
    return MealPlanItem(
        food_id=food_id,
        amount=amount,
        unit=unit,
        serving_id=serving_id,
        grams=grams,
        **macros,
    )


# ---------------------------------------------------------------------------
# Totals roll-up
# ---------------------------------------------------------------------------


def _meal_totals(meal: MealPlanMeal) -> dict[str, Decimal]:
    totals = {k: _ZERO for k in _MACRO_ATTRS}
    for item in meal.items:
        for k in _MACRO_ATTRS:
            value = getattr(item, k)
            if value is not None:
                totals[k] += value
    return {k: v.quantize(_Q) for k, v in totals.items()}


def _day_totals(day: MealPlanDay) -> dict[str, Decimal]:
    totals = {k: _ZERO for k in _MACRO_ATTRS}
    for meal in day.meals:
        mt = _meal_totals(meal)
        for k in _MACRO_ATTRS:
            totals[k] += mt[k]
    return {k: v.quantize(_Q) for k, v in totals.items()}


def _effective_targets(plan: MealPlan, day: MealPlanDay) -> dict[str, Decimal | None]:
    """Per-day override -> plan default -> summed meal totals (when meals exist)."""
    includes_meals = plan.content_mode in (
        MealPlanContentMode.meals_only,
        MealPlanContentMode.targets_and_meals,
    )
    totals = _day_totals(day) if includes_meals else None
    plan_defaults = {
        "target_kcal": plan.target_kcal,
        "target_protein_g": plan.target_protein_g,
        "target_carbs_g": plan.target_carbs_g,
        "target_fat_g": plan.target_fat_g,
    }
    totals_by_target = (
        {
            "target_kcal": totals["kcal"],
            "target_protein_g": totals["protein_g"],
            "target_carbs_g": totals["carbs_g"],
            "target_fat_g": totals["fat_g"],
        }
        if totals is not None
        else {}
    )
    out: dict[str, Decimal | None] = {}
    for field in ("target_kcal", "target_protein_g", "target_carbs_g", "target_fat_g"):
        override = getattr(day, field)
        if override is not None:
            out[field] = override
        elif plan_defaults[field] is not None:
            out[field] = plan_defaults[field]
        elif field in totals_by_target:
            out[field] = totals_by_target[field]
        else:
            out[field] = None
    return out


def serialize_day(plan: MealPlan, day: MealPlanDay) -> dict[str, Any]:
    """Attach totals + effective_targets the response schema expects."""
    meals = []
    for meal in day.meals:
        meals.append(
            {
                "id": meal.id,
                "name": meal.name,
                "slot_index": meal.slot_index,
                "planned_time": meal.planned_time,
                "items": list(meal.items),
                "totals": _meal_totals(meal),
            }
        )
    return {
        "id": day.id,
        "day_role": day.day_role,
        "target_kcal": day.target_kcal,
        "target_protein_g": day.target_protein_g,
        "target_carbs_g": day.target_carbs_g,
        "target_fat_g": day.target_fat_g,
        "meals": meals,
        "totals": _day_totals(day),
        "effective_targets": _effective_targets(plan, day),
    }


def serialize_plan(plan: MealPlan) -> dict[str, Any]:
    return {
        "id": plan.id,
        "name": plan.name,
        "plan_kind": plan.plan_kind,
        "content_mode": plan.content_mode,
        "tracking_mode": plan.tracking_mode,
        "target_kcal": plan.target_kcal,
        "target_protein_g": plan.target_protein_g,
        "target_carbs_g": plan.target_carbs_g,
        "target_fat_g": plan.target_fat_g,
        "target_fiber_g": plan.target_fiber_g,
        "synced_to_program": plan.synced_to_program,
        "training_dows": list(plan.training_dows or []),
        "week_resets": plan.week_resets,
        "week_start_dow": plan.week_start_dow,
        "needs_week_review": plan.needs_week_review,
        "is_active": plan.is_active,
        "activated_at": plan.activated_at,
        "created_at": plan.created_at,
        "day_templates": [serialize_day(plan, d) for d in plan.day_templates],
    }


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _full_load() -> Any:
    return selectinload(MealPlan.day_templates).options(
        selectinload(MealPlanDay.meals).selectinload(MealPlanMeal.items)
    )


async def _owned_plan(session: AsyncSession, user: User, plan_id: UUID) -> MealPlan:
    record = (
        await session.execute(
            select(MealPlan)
            .where(
                MealPlan.id == plan_id,
                MealPlan.user_id == user.id,
                MealPlan.deleted_at.is_(None),
            )
            .options(_full_load())
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Meal plan not found.")
    return record


async def _refresh(session: AsyncSession, plan_id: UUID) -> MealPlan:
    """Reload the plan with all nested rows after a flush so totals are fresh.

    ``expire_all`` forces the selectin loads below to re-read collections from
    the DB rather than reusing identity-mapped collections that were populated
    (possibly empty) before the just-flushed inserts/deletes.
    """
    session.expire_all()
    record = (
        await session.execute(select(MealPlan).where(MealPlan.id == plan_id).options(_full_load()))
    ).scalar_one()
    return record


# ---------------------------------------------------------------------------
# Plan CRUD
# ---------------------------------------------------------------------------


async def create_plan(session: AsyncSession, user: User, payload: Any) -> MealPlan:
    plan = MealPlan(
        user_id=user.id,
        name=payload.name,
        plan_kind=payload.plan_kind,
        content_mode=payload.content_mode,
        tracking_mode=payload.tracking_mode,
        target_kcal=payload.target_kcal,
        target_protein_g=payload.target_protein_g,
        target_carbs_g=payload.target_carbs_g,
        target_fat_g=payload.target_fat_g,
        target_fiber_g=payload.target_fiber_g,
        synced_to_program=payload.synced_to_program,
        training_dows=list(payload.training_dows),
        week_resets=payload.week_resets,
        week_start_dow=payload.week_start_dow,
    )
    session.add(plan)
    await session.flush()

    seen_roles: set[MealPlanDayRole] = set()
    for day_in in payload.day_templates:
        if day_in.day_role in seen_roles:
            raise HTTPException(
                status_code=422,
                detail=f"Duplicate day_role '{day_in.day_role.value}' in plan.",
            )
        seen_roles.add(day_in.day_role)
        day = MealPlanDay(
            meal_plan_id=plan.id,
            day_role=day_in.day_role,
            target_kcal=day_in.target_kcal,
            target_protein_g=day_in.target_protein_g,
            target_carbs_g=day_in.target_carbs_g,
            target_fat_g=day_in.target_fat_g,
        )
        session.add(day)
        await session.flush()
        for meal_in in day_in.meals:
            meal = MealPlanMeal(
                meal_plan_day_id=day.id,
                name=meal_in.name,
                slot_index=meal_in.slot_index,
                planned_time=meal_in.planned_time,
            )
            session.add(meal)
            await session.flush()
            for item_in in meal_in.items:
                item = await _build_item(
                    session,
                    user,
                    food_id=item_in.food_id,
                    amount=item_in.amount,
                    unit=item_in.unit,
                    serving_id=item_in.serving_id,
                )
                item.meal_plan_meal_id = meal.id
                session.add(item)
    await session.flush()
    return await _refresh(session, plan.id)


async def list_plans(session: AsyncSession, user: User) -> list[MealPlan]:
    stmt = (
        select(MealPlan)
        .where(MealPlan.user_id == user.id, MealPlan.deleted_at.is_(None))
        .options(_full_load())
        .order_by(MealPlan.is_active.desc(), MealPlan.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_plan(session: AsyncSession, user: User, plan_id: UUID) -> MealPlan:
    return await _owned_plan(session, user, plan_id)


async def update_plan(
    session: AsyncSession, user: User, plan_id: UUID, updates: dict[str, Any]
) -> MealPlan:
    record = await _owned_plan(session, user, plan_id)
    for field, value in updates.items():
        setattr(record, field, value)
    await session.flush()
    return await _refresh(session, plan_id)


async def soft_delete_plan(session: AsyncSession, user: User, plan_id: UUID) -> None:
    record = await _owned_plan(session, user, plan_id)
    record.deleted_at = _now()
    record.is_active = False
    await session.flush()


async def activate_plan(session: AsyncSession, user: User, plan_id: UUID) -> MealPlan:
    record = await _owned_plan(session, user, plan_id)
    now = _now()
    await session.execute(
        update(MealPlan)
        .where(
            MealPlan.user_id == user.id,
            MealPlan.id != record.id,
            MealPlan.is_active.is_(True),
        )
        .values(is_active=False, updated_at=now)
    )
    record.is_active = True
    record.activated_at = now
    await session.flush()
    return await _refresh(session, plan_id)


# ---------------------------------------------------------------------------
# Nested day / meal / item CRUD
# ---------------------------------------------------------------------------


async def _owned_day(session: AsyncSession, user: User, day_id: UUID) -> MealPlanDay:
    record = (
        await session.execute(
            select(MealPlanDay)
            .join(MealPlan, MealPlan.id == MealPlanDay.meal_plan_id)
            .where(
                MealPlanDay.id == day_id,
                MealPlan.user_id == user.id,
                MealPlan.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Day template not found.")
    return record


async def _owned_meal(session: AsyncSession, user: User, meal_id: UUID) -> MealPlanMeal:
    record = (
        await session.execute(
            select(MealPlanMeal)
            .join(MealPlanDay, MealPlanDay.id == MealPlanMeal.meal_plan_day_id)
            .join(MealPlan, MealPlan.id == MealPlanDay.meal_plan_id)
            .where(
                MealPlanMeal.id == meal_id,
                MealPlan.user_id == user.id,
                MealPlan.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Planned meal not found.")
    return record


async def _owned_item(session: AsyncSession, user: User, item_id: UUID) -> MealPlanItem:
    record = (
        await session.execute(
            select(MealPlanItem)
            .join(MealPlanMeal, MealPlanMeal.id == MealPlanItem.meal_plan_meal_id)
            .join(MealPlanDay, MealPlanDay.id == MealPlanMeal.meal_plan_day_id)
            .join(MealPlan, MealPlan.id == MealPlanDay.meal_plan_id)
            .where(
                MealPlanItem.id == item_id,
                MealPlan.user_id == user.id,
                MealPlan.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Planned item not found.")
    return record


async def add_day(session: AsyncSession, user: User, plan_id: UUID, payload: Any) -> MealPlan:
    plan = await _owned_plan(session, user, plan_id)
    if any(d.day_role == payload.day_role for d in plan.day_templates):
        raise HTTPException(
            status_code=409,
            detail=f"Day template '{payload.day_role.value}' already exists.",
        )
    day = MealPlanDay(
        meal_plan_id=plan.id,
        day_role=payload.day_role,
        target_kcal=payload.target_kcal,
        target_protein_g=payload.target_protein_g,
        target_carbs_g=payload.target_carbs_g,
        target_fat_g=payload.target_fat_g,
    )
    session.add(day)
    await session.flush()
    for meal_in in payload.meals:
        meal = MealPlanMeal(
            meal_plan_day_id=day.id,
            name=meal_in.name,
            slot_index=meal_in.slot_index,
            planned_time=meal_in.planned_time,
        )
        session.add(meal)
        await session.flush()
        for item_in in meal_in.items:
            item = await _build_item(
                session,
                user,
                food_id=item_in.food_id,
                amount=item_in.amount,
                unit=item_in.unit,
                serving_id=item_in.serving_id,
            )
            item.meal_plan_meal_id = meal.id
            session.add(item)
    await session.flush()
    return await _refresh(session, plan_id)


async def update_day(
    session: AsyncSession, user: User, day_id: UUID, updates: dict[str, Any]
) -> MealPlan:
    day = await _owned_day(session, user, day_id)
    for field, value in updates.items():
        setattr(day, field, value)
    await session.flush()
    return await _refresh(session, day.meal_plan_id)


async def delete_day(session: AsyncSession, user: User, day_id: UUID) -> MealPlan:
    day = await _owned_day(session, user, day_id)
    plan_id = day.meal_plan_id
    await session.delete(day)
    await session.flush()
    return await _refresh(session, plan_id)


async def add_meal(session: AsyncSession, user: User, day_id: UUID, payload: Any) -> MealPlan:
    day = await _owned_day(session, user, day_id)
    meal = MealPlanMeal(
        meal_plan_day_id=day.id,
        name=payload.name,
        slot_index=payload.slot_index,
        planned_time=payload.planned_time,
    )
    session.add(meal)
    await session.flush()
    for item_in in payload.items:
        item = await _build_item(
            session,
            user,
            food_id=item_in.food_id,
            amount=item_in.amount,
            unit=item_in.unit,
            serving_id=item_in.serving_id,
        )
        item.meal_plan_meal_id = meal.id
        session.add(item)
    await session.flush()
    return await _refresh(session, day.meal_plan_id)


async def update_meal(
    session: AsyncSession, user: User, meal_id: UUID, updates: dict[str, Any]
) -> MealPlan:
    meal = await _owned_meal(session, user, meal_id)
    for field, value in updates.items():
        setattr(meal, field, value)
    await session.flush()
    day = await _owned_day_of_meal(session, meal)
    return await _refresh(session, day.meal_plan_id)


async def delete_meal(session: AsyncSession, user: User, meal_id: UUID) -> MealPlan:
    meal = await _owned_meal(session, user, meal_id)
    day = await _owned_day_of_meal(session, meal)
    plan_id = day.meal_plan_id
    await session.delete(meal)
    await session.flush()
    return await _refresh(session, plan_id)


async def _owned_day_of_meal(session: AsyncSession, meal: MealPlanMeal) -> MealPlanDay:
    return (
        await session.execute(select(MealPlanDay).where(MealPlanDay.id == meal.meal_plan_day_id))
    ).scalar_one()


async def add_item(session: AsyncSession, user: User, meal_id: UUID, payload: Any) -> MealPlan:
    meal = await _owned_meal(session, user, meal_id)
    item = await _build_item(
        session,
        user,
        food_id=payload.food_id,
        amount=payload.amount,
        unit=payload.unit,
        serving_id=payload.serving_id,
    )
    item.meal_plan_meal_id = meal.id
    session.add(item)
    await session.flush()
    day = await _owned_day_of_meal(session, meal)
    return await _refresh(session, day.meal_plan_id)


async def update_item(session: AsyncSession, user: User, item_id: UUID, payload: Any) -> MealPlan:
    item = await _owned_item(session, user, item_id)
    food_id = payload.food_id if payload.food_id is not None else item.food_id
    amount = payload.amount if payload.amount is not None else item.amount
    unit = payload.unit if payload.unit is not None else item.unit
    serving_id = payload.serving_id if "serving_id" in payload.model_fields_set else item.serving_id

    rebuilt = await _build_item(
        session, user, food_id=food_id, amount=amount, unit=unit, serving_id=serving_id
    )
    item.food_id = rebuilt.food_id
    item.amount = rebuilt.amount
    item.unit = rebuilt.unit
    item.serving_id = rebuilt.serving_id
    item.grams = rebuilt.grams
    for k in _MACRO_ATTRS:
        setattr(item, k, getattr(rebuilt, k))
    await session.flush()

    meal = await _owned_meal(session, user, item.meal_plan_meal_id)
    day = await _owned_day_of_meal(session, meal)
    return await _refresh(session, day.meal_plan_id)


async def delete_item(session: AsyncSession, user: User, item_id: UUID) -> MealPlan:
    item = await _owned_item(session, user, item_id)
    meal_id = item.meal_plan_meal_id
    await session.delete(item)
    await session.flush()
    meal = await _owned_meal(session, user, meal_id)
    day = await _owned_day_of_meal(session, meal)
    return await _refresh(session, day.meal_plan_id)


# ---------------------------------------------------------------------------
# Calendar resolution
# ---------------------------------------------------------------------------


async def _is_training_day(session: AsyncSession, user: User, day: date) -> bool:
    """A date is a training day when the user has a ScheduledWorkout on it."""
    row = (
        await session.execute(
            select(ScheduledWorkout.id)
            .where(
                ScheduledWorkout.user_id == user.id,
                ScheduledWorkout.scheduled_for == day,
            )
            .limit(1)
        )
    ).first()
    return row is not None


def _days_by_role(plan: MealPlan) -> dict[MealPlanDayRole, MealPlanDay]:
    return {d.day_role: d for d in plan.day_templates}


async def resolve_role(
    session: AsyncSession, user: User, plan: MealPlan, day: date
) -> tuple[MealPlanDayRole, bool | None]:
    """Return (day_role, is_training_day) for ``day`` under ``plan``."""
    if plan.plan_kind == MealPlanKind.daily_repeating:
        return MealPlanDayRole.every_day, None
    if plan.plan_kind == MealPlanKind.training_rest:
        if plan.synced_to_program:
            training = await _is_training_day(session, user, day)
        else:
            training = day.weekday() in set(plan.training_dows or [])
        return (
            MealPlanDayRole.training if training else MealPlanDayRole.rest,
            training,
        )
    # weekly
    role = MealPlanDayRole(f"dow_{day.weekday()}")
    return role, None


def _apply_week_review(plan: MealPlan, day: date) -> None:
    """For weekly plans with week_resets: once the calendar has reached the
    configured week start (and the active activation predates the current
    week), flag needs_week_review so the client can prompt. Non-blocking; we
    only set the flag, never clear it here (the user clears it via PATCH).
    """
    if plan.plan_kind != MealPlanKind.weekly or not plan.week_resets:
        return
    anchor = plan.activated_at.date() if plan.activated_at is not None else plan.created_at.date()
    if _week_index(day, plan.week_start_dow) > _week_index(anchor, plan.week_start_dow):
        plan.needs_week_review = True


def _week_index(day: date, week_start_dow: int) -> int:
    """Ordinal of the week containing ``day``, where weeks begin on
    ``week_start_dow`` (0=Monday)."""
    offset = (day.weekday() - week_start_dow) % 7
    week_start = day.toordinal() - offset
    return week_start // 7


async def resolve_day(
    session: AsyncSession, user: User, plan: MealPlan, day: date
) -> dict[str, Any]:
    """Resolve which day template applies on ``day`` and roll up its targets."""
    _apply_week_review(plan, day)
    role, is_training = await resolve_role(session, user, plan, day)
    template = _days_by_role(plan).get(role)
    if template is not None:
        targets = _effective_targets(plan, template)
        template_payload: dict[str, Any] | None = serialize_day(plan, template)
    else:
        targets = {
            "target_kcal": plan.target_kcal,
            "target_protein_g": plan.target_protein_g,
            "target_carbs_g": plan.target_carbs_g,
            "target_fat_g": plan.target_fat_g,
        }
        template_payload = None
    return {
        "date": day,
        "day_role": role,
        "is_training_day": is_training,
        "effective_targets": targets,
        "tracking_mode": plan.tracking_mode,
        "template": template_payload,
    }


# ---------------------------------------------------------------------------
# Active plan + progress
# ---------------------------------------------------------------------------


async def get_active_plan(session: AsyncSession, user: User) -> MealPlan | None:
    return (
        await session.execute(
            select(MealPlan)
            .where(
                MealPlan.user_id == user.id,
                MealPlan.is_active.is_(True),
                MealPlan.deleted_at.is_(None),
            )
            .options(_full_load())
        )
    ).scalar_one_or_none()


async def active_with_progress(
    session: AsyncSession,
    user: User,
    *,
    day: date,
    tz_offset_minutes: int = 0,
) -> dict[str, Any] | None:
    """Active plan + resolved day template + today's consumed/remaining macros."""
    plan = await get_active_plan(session, user)
    if plan is None:
        return None

    resolved = await resolve_day(session, user, plan, day)

    from app.services import meals as meals_svc

    summary = await meals_svc.daily_summary(
        session, user, day=day, tz_offset_minutes=tz_offset_minutes
    )
    totals = summary["totals"]

    targets = resolved["effective_targets"]
    remaining = {
        "kcal": (targets["target_kcal"] or _ZERO) - totals["kcal"],
        "protein_g": (targets["target_protein_g"] or _ZERO) - totals["protein_g"],
        "carbs_g": (targets["target_carbs_g"] or _ZERO) - totals["carbs_g"],
        "fat_g": (targets["target_fat_g"] or _ZERO) - totals["fat_g"],
    }
    return {
        "plan": plan,
        "resolved_day": resolved,
        "consumed": totals,
        "remaining": remaining,
        "date": day,
    }
