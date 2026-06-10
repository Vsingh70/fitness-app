"""Meals + meal_items CRUD with macro denormalization.

Denormalization rule:
- On `add_item`: pull current food row, compute kcal/protein/carbs/fat/fiber
  for the logged grams, store on the meal_items row.
- On `update_item.grams`: scale the stored macros proportionally from the
  existing snapshot. Edits to the foods row never rewrite past items.
- On `update_item.food_id`: full re-pull from foods (treat it as if the user
  re-added the item).
- Hard delete on meal_items (no soft delete).

Amount/unit: items accept (amount, unit g|ml|serving, serving_id) just like
``meal_plan_items``. The amount->grams resolution + validation is shared via
``meal_plans.resolve_grams`` / ``load_serving`` so logging and planning agree.
A grams-only body still works (treated as unit=g, amount=grams).
"""

from __future__ import annotations

import contextlib
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import asc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import MealPlanItemUnit, MealType
from app.models.food import Food
from app.models.meal import Meal, MealItem
from app.models.meal_plan import MealPlanMeal
from app.models.user import User
from app.observability.spans import traced_span
from app.services import meal_plans as plans_svc

_PER_100G_ATTRS = (
    ("kcal", "kcal_per_100g"),
    ("protein_g", "protein_g_per_100g"),
    ("carbs_g", "carbs_g_per_100g"),
    ("fat_g", "fat_g_per_100g"),
    ("fiber_g", "fiber_g_per_100g"),
)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _scale_for_grams(per_100g: Decimal | None, grams: Decimal) -> Decimal | None:
    if per_100g is None:
        return None
    return (per_100g * grams / Decimal("100")).quantize(Decimal("0.01"))


def _macros_from_food(food: Food, grams: Decimal) -> dict[str, Decimal | None]:
    return {
        target: _scale_for_grams(getattr(food, source), grams) for target, source in _PER_100G_ATTRS
    }


# ---------------------------------------------------------------------------
# Meals
# ---------------------------------------------------------------------------


async def create_meal(
    session: AsyncSession,
    user: User,
    *,
    eaten_at: datetime,
    meal_type: MealType,
    notes: str | None = None,
) -> Meal:
    record = Meal(
        user_id=user.id,
        eaten_at=eaten_at,
        meal_type=meal_type,
        notes=notes,
    )
    session.add(record)
    await session.flush()
    return record


async def _owned_meal(
    session: AsyncSession, user: User, meal_id: UUID, *, allow_deleted: bool = False
) -> Meal:
    conditions = [Meal.id == meal_id, Meal.user_id == user.id]
    if not allow_deleted:
        conditions.append(Meal.deleted_at.is_(None))
    stmt = select(Meal).where(*conditions).options(selectinload(Meal.items))
    record = (await session.execute(stmt)).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Meal not found.")
    return record


async def get_meal(session: AsyncSession, user: User, meal_id: UUID) -> Meal:
    return await _owned_meal(session, user, meal_id)


async def list_meals(
    session: AsyncSession,
    user: User,
    *,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
    meal_type: MealType | None = None,
) -> list[Meal]:
    stmt = (
        select(Meal)
        .where(Meal.user_id == user.id, Meal.deleted_at.is_(None))
        .options(selectinload(Meal.items))
        .order_by(asc(Meal.eaten_at))
    )
    if from_dt is not None:
        stmt = stmt.where(Meal.eaten_at >= from_dt)
    if to_dt is not None:
        stmt = stmt.where(Meal.eaten_at <= to_dt)
    if meal_type is not None:
        stmt = stmt.where(Meal.meal_type == meal_type)
    return list((await session.execute(stmt)).scalars().all())


async def update_meal(
    session: AsyncSession, user: User, meal_id: UUID, updates: dict[str, Any]
) -> Meal:
    record = await _owned_meal(session, user, meal_id)
    for field, value in updates.items():
        setattr(record, field, value)
    await session.flush()
    return record


async def soft_delete_meal(
    session: AsyncSession, user: User, meal_id: UUID, *, forever: bool = False
) -> None:
    """Soft-delete a logged meal.

    ``forever`` also removes the plan-template meal this logged meal was
    materialized from (via ``source_plan_meal_id``) so it stops appearing on
    future plan days. For a non-plan meal, ``forever`` behaves like the default.
    """
    record = await _owned_meal(session, user, meal_id)
    record.deleted_at = _now()
    if forever and record.source_plan_meal_id is not None:
        # Ownership is implied: the meal is the user's, and the FK chains to
        # their plan. delete_meal re-verifies ownership defensively. If the
        # template meal is already gone, the logged meal is still soft-deleted,
        # which satisfies the "today" semantics.
        with contextlib.suppress(HTTPException):
            await plans_svc.delete_meal(session, user, record.source_plan_meal_id)
    await session.flush()


# ---------------------------------------------------------------------------
# Meal items
# ---------------------------------------------------------------------------


async def _resolve_food_for_user(session: AsyncSession, user: User, food_id: UUID) -> Food:
    record = (await session.execute(select(Food).where(Food.id == food_id))).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Food not found.")
    if record.owner_id is not None and record.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Food not found.")
    return record


async def _resolve_amount_to_grams(
    session: AsyncSession,
    user: User,
    *,
    food_id: UUID,
    amount: Decimal | None,
    unit: MealPlanItemUnit,
    serving_id: UUID | None,
    grams: Decimal | None,
) -> tuple[Decimal, Decimal]:
    """Return (amount, grams) for an item body.

    Back-compat: a ``grams``-only body (no amount) is treated as unit=g with
    amount==grams. Otherwise the shared meal-plan resolver converts
    (amount, unit, serving) to canonical grams.
    """
    if amount is None:
        if grams is None:
            raise HTTPException(status_code=422, detail="amount or grams is required")
        if grams <= 0:
            raise HTTPException(status_code=422, detail="grams must be > 0")
        return grams, grams
    serving: Any = None
    if unit == MealPlanItemUnit.serving:
        if serving_id is None:
            raise HTTPException(status_code=422, detail="serving_id required for unit 'serving'.")
        serving = await plans_svc.load_serving(session, food_id, serving_id)
    elif serving_id is not None:
        raise HTTPException(status_code=422, detail="serving_id only valid when unit is 'serving'.")
    if amount <= 0:
        raise HTTPException(status_code=422, detail="amount must be > 0")
    resolved = plans_svc.resolve_grams(amount=amount, unit=unit, serving=serving)
    return amount, resolved


async def add_item(
    session: AsyncSession,
    user: User,
    meal_id: UUID,
    *,
    food_id: UUID,
    grams: Decimal | None = None,
    amount: Decimal | None = None,
    unit: MealPlanItemUnit = MealPlanItemUnit.g,
    serving_id: UUID | None = None,
) -> MealItem:
    meal = await _owned_meal(session, user, meal_id)
    food = await _resolve_food_for_user(session, user, food_id)
    resolved_amount, resolved_grams = await _resolve_amount_to_grams(
        session,
        user,
        food_id=food_id,
        amount=amount,
        unit=unit,
        serving_id=serving_id,
        grams=grams,
    )
    with traced_span(
        "db.tx.meals",
        user_id=user.id,
        attributes={"meal.id": str(meal.id)},
    ):
        item = MealItem(
            meal_id=meal.id,
            food_id=food.id,
            amount=resolved_amount,
            unit=unit,
            serving_id=serving_id,
            grams=resolved_grams,
            **_macros_from_food(food, resolved_grams),
        )
        session.add(item)
        await session.flush()
        return item


async def _owned_item(session: AsyncSession, user: User, item_id: UUID) -> MealItem:
    record = (
        await session.execute(
            select(MealItem)
            .join(Meal, Meal.id == MealItem.meal_id)
            .where(
                MealItem.id == item_id,
                Meal.user_id == user.id,
                Meal.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Meal item not found.")
    return record


async def update_item(
    session: AsyncSession,
    user: User,
    item_id: UUID,
    *,
    grams: Decimal | None = None,
    food_id: UUID | None = None,
    amount: Decimal | None = None,
    unit: MealPlanItemUnit | None = None,
    serving_id: UUID | None = None,
    serving_id_set: bool = False,
) -> MealItem:
    record = await _owned_item(session, user, item_id)

    food_changed = food_id is not None and food_id != record.food_id
    # An amount/unit/serving edit re-resolves grams (and thus macros) from scratch.
    amount_changed = amount is not None or unit is not None or serving_id_set

    if food_changed or amount_changed:
        eff_food_id = food_id if food_id is not None else record.food_id
        food = await _resolve_food_for_user(session, user, eff_food_id)
        eff_unit = unit if unit is not None else record.unit
        eff_serving_id = serving_id if serving_id_set else record.serving_id
        eff_amount = amount if amount is not None else record.amount
        resolved_amount, resolved_grams = await _resolve_amount_to_grams(
            session,
            user,
            food_id=eff_food_id,
            amount=eff_amount,
            unit=eff_unit,
            serving_id=eff_serving_id,
            grams=record.grams,
        )
        record.food_id = food.id
        record.amount = resolved_amount
        record.unit = eff_unit
        record.serving_id = eff_serving_id
        record.grams = resolved_grams
        for target, value in _macros_from_food(food, resolved_grams).items():
            setattr(record, target, value)
    elif grams is not None and grams != record.grams:
        if grams <= 0:
            raise HTTPException(status_code=422, detail="grams must be > 0")
        # Scale stored macros from old grams to new grams (preserves the
        # historical food snapshot). Also keep amount aligned for unit=g/ml.
        ratio = grams / record.grams
        for target, _ in _PER_100G_ATTRS:
            current = getattr(record, target)
            if current is not None:
                setattr(record, target, (current * ratio).quantize(Decimal("0.01")))
        if record.unit in (MealPlanItemUnit.g, MealPlanItemUnit.ml):
            record.amount = grams
        record.grams = grams
    await session.flush()
    return record


async def delete_item(session: AsyncSession, user: User, item_id: UUID) -> None:
    record = await _owned_item(session, user, item_id)
    await session.delete(record)
    await session.flush()


# ---------------------------------------------------------------------------
# Mark planned meal complete + swap
# ---------------------------------------------------------------------------


_PLAN_TYPE_BY_KEYWORD = (
    ("breakfast", MealType.breakfast),
    ("lunch", MealType.lunch),
    ("dinner", MealType.dinner),
    ("snack", MealType.snack),
)


def _meal_type_for_plan_meal(plan_meal: MealPlanMeal) -> MealType:
    """Best-effort map a planned meal's name to a MealType; default to snack."""
    name = (plan_meal.name or "").lower()
    for keyword, meal_type in _PLAN_TYPE_BY_KEYWORD:
        if keyword in name:
            return meal_type
    return MealType.snack


def _items_from_plan_meal(meal: Meal, plan_meal: MealPlanMeal) -> list[MealItem]:
    """Copy a planned meal's items into fresh MealItem rows (macros are copied
    from the plan item's already-denormalized snapshot; fiber is recomputed-free
    since plan items don't carry it)."""
    items: list[MealItem] = []
    for src in plan_meal.items:
        items.append(
            MealItem(
                meal_id=meal.id,
                food_id=src.food_id,
                amount=src.amount,
                unit=src.unit,
                serving_id=src.serving_id,
                grams=src.grams,
                kcal=src.kcal,
                protein_g=src.protein_g,
                carbs_g=src.carbs_g,
                fat_g=src.fat_g,
                fiber_g=None,
            )
        )
    return items


async def _existing_completion(
    session: AsyncSession, user: User, plan_meal_id: UUID, day: date
) -> Meal | None:
    stmt = (
        select(Meal)
        .where(
            Meal.user_id == user.id,
            Meal.source_plan_meal_id == plan_meal_id,
            Meal.source_plan_date == day,
            Meal.deleted_at.is_(None),
        )
        .options(selectinload(Meal.items))
        .order_by(asc(Meal.created_at))
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def complete_planned_meal(
    session: AsyncSession,
    user: User,
    plan_id: UUID,
    plan_meal_id: UUID,
    *,
    day: date,
) -> Meal:
    """Materialize a planned meal into a logged ``meal`` (+ items) for ``day``.

    Idempotent per (plan_meal, date): if a non-deleted completion already exists
    it is returned instead of creating a duplicate.
    """
    plan = await plans_svc.get_plan(session, user, plan_id)
    plan_meal = await plans_svc._owned_meal(session, user, plan_meal_id)
    plan_day = await plans_svc._owned_day_of_meal(session, plan_meal)
    if plan_day.meal_plan_id != plan.id:
        raise HTTPException(status_code=404, detail="Planned meal not found in this plan.")

    existing = await _existing_completion(session, user, plan_meal_id, day)
    if existing is not None:
        return existing

    if plan_meal.planned_time is not None:
        eaten_at = datetime.combine(day, plan_meal.planned_time, tzinfo=UTC)
    else:
        eaten_at = _now()

    meal = Meal(
        user_id=user.id,
        eaten_at=eaten_at,
        meal_type=_meal_type_for_plan_meal(plan_meal),
        notes=plan_meal.name,
        source_plan_meal_id=plan_meal.id,
        source_plan_date=day,
    )
    session.add(meal)
    await session.flush()
    for item in _items_from_plan_meal(meal, plan_meal):
        session.add(item)
    await session.flush()
    return await _owned_meal(session, user, meal.id)


async def swap_meal(
    session: AsyncSession,
    user: User,
    meal_id: UUID,
    *,
    plan_meal_id: UUID | None = None,
    items: list[Any] | None = None,
) -> Meal:
    """Replace a logged meal's items, either from a planned meal or a provided
    item list. Clears existing items and inserts the new set, re-denormalizing.
    """
    if (plan_meal_id is None) == (items is None):
        raise HTTPException(
            status_code=422,
            detail="Provide exactly one of plan_meal_id or items.",
        )
    meal = await _owned_meal(session, user, meal_id)

    new_items: list[MealItem]
    if plan_meal_id is not None:
        plan_meal = await plans_svc._owned_meal(session, user, plan_meal_id)
        new_items = _items_from_plan_meal(meal, plan_meal)
    else:
        assert items is not None
        new_items = []
        for body in items:
            food = await _resolve_food_for_user(session, user, body.food_id)
            resolved_amount, resolved_grams = await _resolve_amount_to_grams(
                session,
                user,
                food_id=body.food_id,
                amount=body.amount,
                unit=body.unit,
                serving_id=body.serving_id,
                grams=body.grams,
            )
            new_items.append(
                MealItem(
                    food_id=food.id,
                    amount=resolved_amount,
                    unit=body.unit,
                    serving_id=body.serving_id,
                    grams=resolved_grams,
                    **_macros_from_food(food, resolved_grams),
                )
            )

    # Clear existing items then insert the replacement set. Replacing the
    # relationship collection in one assignment lets delete-orphan remove the
    # old rows and cascade-insert the new ones atomically.
    meal.items = new_items
    await session.flush()
    return await _owned_meal(session, user, meal.id)


# ---------------------------------------------------------------------------
# Daily summary
# ---------------------------------------------------------------------------


def _day_bounds(day: date, tz_offset_minutes: int = 0) -> tuple[datetime, datetime]:
    """Return UTC-bounded window for a calendar day. tz_offset_minutes lets
    callers shift the boundary to the user's local timezone if needed; the
    web client passes the offset.
    """
    from datetime import timezone as tz

    offset = tz(timedelta(minutes=tz_offset_minutes))
    start_local = datetime.combine(day, datetime.min.time(), tzinfo=offset)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


async def daily_summary(
    session: AsyncSession,
    user: User,
    *,
    day: date,
    tz_offset_minutes: int = 0,
    include_adherence: bool = False,
) -> dict[str, Any]:
    """Aggregate macros across non-deleted meals in the local day window.

    Returns:
    {
      "date": "2026-05-25",
      "totals": {"kcal": ..., "protein_g": ..., "carbs_g": ..., "fat_g": ..., "fiber_g": ...},
      "per_meal": [{"meal_id", "meal_type", "eaten_at", "totals": {...}, "items": [...]}],
      "adherence": {...} | None,   # only when include_adherence
      "tracking_mode": <str> | None,
    }
    """
    start_utc, end_utc = _day_bounds(day, tz_offset_minutes)
    meals = await list_meals(session, user, from_dt=start_utc, to_dt=end_utc)
    totals = {target: Decimal("0") for target, _ in _PER_100G_ATTRS}
    per_meal: list[dict[str, Any]] = []
    for meal in meals:
        meal_totals = {target: Decimal("0") for target, _ in _PER_100G_ATTRS}
        for item in meal.items:
            for target, _ in _PER_100G_ATTRS:
                value = getattr(item, target)
                if value is not None:
                    meal_totals[target] += value
        for target, _ in _PER_100G_ATTRS:
            totals[target] += meal_totals[target]
        per_meal.append(
            {
                "meal_id": meal.id,
                "meal_type": meal.meal_type,
                "eaten_at": meal.eaten_at,
                "totals": {k: v.quantize(Decimal("0.01")) for k, v in meal_totals.items()},
                "items": list(meal.items),
            }
        )
    result: dict[str, Any] = {
        "date": day,
        "totals": {k: v.quantize(Decimal("0.01")) for k, v in totals.items()},
        "per_meal": per_meal,
    }
    if include_adherence:
        result["adherence"], result["tracking_mode"] = await _plan_adherence(
            session, user, day=day, logged_meals=meals
        )
    return result


async def _plan_adherence(
    session: AsyncSession, user: User, *, day: date, logged_meals: list[Meal]
) -> tuple[dict[str, Any] | None, str | None]:
    """For the active plan's resolved day, count how many planned meals have a
    completed (non-deleted) logged meal for this date. Returns (adherence,
    tracking_mode); both None when no plan is active.
    """
    plan = await plans_svc.get_active_plan(session, user)
    if plan is None:
        return None, None
    resolved = await plans_svc.resolve_day(session, user, plan, day)
    template = resolved.get("template")
    planned_meal_ids: list[UUID] = []
    if template is not None:
        for meal in template["meals"]:
            planned_meal_ids.append(meal["id"])
    completed_ids = {
        m.source_plan_meal_id
        for m in logged_meals
        if m.source_plan_meal_id is not None and m.source_plan_date == day
    }
    completed = sum(1 for pid in planned_meal_ids if pid in completed_ids)
    adherence = {
        "planned_meals": len(planned_meal_ids),
        "completed_meals": completed,
        "completed_plan_meal_ids": [pid for pid in planned_meal_ids if pid in completed_ids],
    }
    return adherence, str(plan.tracking_mode)
