"""body_metrics CRUD. Daily weight log + body fat percentage."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.body_metric import BodyMetric
from app.models.user import User


async def log_metric(
    session: AsyncSession,
    user: User,
    *,
    recorded_at: datetime,
    weight_kg: Decimal | None = None,
    body_fat_pct: Decimal | None = None,
) -> BodyMetric:
    record = BodyMetric(
        user_id=user.id,
        recorded_at=recorded_at,
        weight_kg=weight_kg,
        body_fat_pct=body_fat_pct,
    )
    session.add(record)
    await session.flush()
    return record


async def list_metrics(
    session: AsyncSession,
    user: User,
    *,
    limit: int = 100,
) -> list[BodyMetric]:
    stmt = (
        select(BodyMetric)
        .where(BodyMetric.user_id == user.id)
        .order_by(desc(BodyMetric.recorded_at))
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def delete_metric(session: AsyncSession, user: User, metric_id: UUID) -> None:
    record = (
        await session.execute(
            select(BodyMetric).where(BodyMetric.id == metric_id, BodyMetric.user_id == user.id)
        )
    ).scalar_one_or_none()
    if record is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Body metric not found.")
    await session.delete(record)
    await session.flush()
