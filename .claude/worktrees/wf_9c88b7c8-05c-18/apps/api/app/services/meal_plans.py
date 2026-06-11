"""Meal plan CRUD + single-active activation."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meal_plan import MealPlan
from app.models.user import User


def _now() -> datetime:
    return datetime.now(tz=UTC)


async def create_plan(
    session: AsyncSession,
    user: User,
    *,
    name: str,
    target_kcal: Decimal,
    target_protein_g: Decimal,
    target_carbs_g: Decimal,
    target_fat_g: Decimal,
    target_fiber_g: Decimal | None = None,
    days: dict[str, Any] | None = None,
) -> MealPlan:
    record = MealPlan(
        user_id=user.id,
        name=name,
        target_kcal=target_kcal,
        target_protein_g=target_protein_g,
        target_carbs_g=target_carbs_g,
        target_fat_g=target_fat_g,
        target_fiber_g=target_fiber_g,
        days=days or {},
    )
    session.add(record)
    await session.flush()
    return record


async def _owned_plan(session: AsyncSession, user: User, plan_id: UUID) -> MealPlan:
    record = (
        await session.execute(
            select(MealPlan).where(
                MealPlan.id == plan_id,
                MealPlan.user_id == user.id,
                MealPlan.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Meal plan not found.")
    return record


async def list_plans(session: AsyncSession, user: User) -> list[MealPlan]:
    stmt = (
        select(MealPlan)
        .where(MealPlan.user_id == user.id, MealPlan.deleted_at.is_(None))
        .order_by(MealPlan.is_active.desc(), MealPlan.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def update_plan(
    session: AsyncSession, user: User, plan_id: UUID, updates: dict[str, Any]
) -> MealPlan:
    record = await _owned_plan(session, user, plan_id)
    for field, value in updates.items():
        setattr(record, field, value)
    await session.flush()
    return record


async def soft_delete_plan(session: AsyncSession, user: User, plan_id: UUID) -> None:
    record = await _owned_plan(session, user, plan_id)
    record.deleted_at = _now()
    record.is_active = False
    await session.flush()


async def activate_plan(session: AsyncSession, user: User, plan_id: UUID) -> MealPlan:
    """Mark this plan active and deactivate all the user's other plans."""
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
    return record


async def get_active_plan(session: AsyncSession, user: User) -> MealPlan | None:
    return (
        await session.execute(
            select(MealPlan).where(
                MealPlan.user_id == user.id,
                MealPlan.is_active.is_(True),
                MealPlan.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()


async def active_with_progress(
    session: AsyncSession,
    user: User,
    *,
    day: date,
    tz_offset_minutes: int = 0,
) -> dict[str, Any] | None:
    """Return the active plan plus today's actual totals + remaining."""
    plan = await get_active_plan(session, user)
    if plan is None:
        return None
    from app.services import meals as meals_svc

    summary = await meals_svc.daily_summary(
        session, user, day=day, tz_offset_minutes=tz_offset_minutes
    )
    totals = summary["totals"]
    remaining = {
        "kcal": plan.target_kcal - totals["kcal"],
        "protein_g": plan.target_protein_g - totals["protein_g"],
        "carbs_g": plan.target_carbs_g - totals["carbs_g"],
        "fat_g": plan.target_fat_g - totals["fat_g"],
    }
    return {
        "plan": plan,
        "consumed": totals,
        "remaining": remaining,
        "date": day,
    }
