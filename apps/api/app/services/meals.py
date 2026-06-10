"""Meals + meal_items CRUD with macro denormalization.

Denormalization rule:
- On `add_item`: pull current food row, compute kcal/protein/carbs/fat/fiber
  for the logged grams, store on the meal_items row.
- On `update_item.grams`: scale the stored macros proportionally from the
  existing snapshot. Edits to the foods row never rewrite past items.
- On `update_item.food_id`: full re-pull from foods (treat it as if the user
  re-added the item).
- Hard delete on meal_items (no soft delete).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import asc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import MealType
from app.models.food import Food
from app.models.meal import Meal, MealItem
from app.models.user import User
from app.observability.spans import traced_span

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


async def soft_delete_meal(session: AsyncSession, user: User, meal_id: UUID) -> None:
    record = await _owned_meal(session, user, meal_id)
    record.deleted_at = _now()
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


async def add_item(
    session: AsyncSession,
    user: User,
    meal_id: UUID,
    *,
    food_id: UUID,
    grams: Decimal,
) -> MealItem:
    if grams <= 0:
        raise HTTPException(status_code=422, detail="grams must be > 0")
    meal = await _owned_meal(session, user, meal_id)
    food = await _resolve_food_for_user(session, user, food_id)
    with traced_span(
        "db.tx.meals",
        user_id=user.id,
        attributes={"meal.id": str(meal.id)},
    ):
        item = MealItem(
            meal_id=meal.id,
            food_id=food.id,
            grams=grams,
            **_macros_from_food(food, grams),
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
) -> MealItem:
    record = await _owned_item(session, user, item_id)
    if food_id is not None and food_id != record.food_id:
        # Full re-pull from foods, scaled to current (or new) grams.
        food = await _resolve_food_for_user(session, user, food_id)
        new_grams = grams if grams is not None else record.grams
        if new_grams <= 0:
            raise HTTPException(status_code=422, detail="grams must be > 0")
        record.food_id = food.id
        record.grams = new_grams
        for target, value in _macros_from_food(food, new_grams).items():
            setattr(record, target, value)
    elif grams is not None and grams != record.grams:
        if grams <= 0:
            raise HTTPException(status_code=422, detail="grams must be > 0")
        # Scale stored macros from old grams to new grams (preserves the
        # historical food snapshot).
        ratio = grams / record.grams
        for target, _ in _PER_100G_ATTRS:
            current = getattr(record, target)
            if current is not None:
                setattr(record, target, (current * ratio).quantize(Decimal("0.01")))
        record.grams = grams
    await session.flush()
    return record


async def delete_item(session: AsyncSession, user: User, item_id: UUID) -> None:
    record = await _owned_item(session, user, item_id)
    await session.delete(record)
    await session.flush()


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
    session: AsyncSession, user: User, *, day: date, tz_offset_minutes: int = 0
) -> dict[str, Any]:
    """Aggregate macros across non-deleted meals in the local day window.

    Returns:
    {
      "date": "2026-05-25",
      "totals": {"kcal": ..., "protein_g": ..., "carbs_g": ..., "fat_g": ..., "fiber_g": ...},
      "per_meal": [{"meal_id", "meal_type", "eaten_at", "totals": {...}, "items": [...]}]
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
    return {
        "date": day,
        "totals": {k: v.quantize(Decimal("0.01")) for k, v in totals.items()},
        "per_meal": per_meal,
    }
