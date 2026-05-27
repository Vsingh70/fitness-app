from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import Recommendation
from app.models.user import User


def _now() -> datetime:
    return datetime.now(tz=UTC)


async def list_active(session: AsyncSession, user: User) -> list[Recommendation]:
    stmt = (
        select(Recommendation)
        .where(
            Recommendation.user_id == user.id,
            Recommendation.consumed_at.is_(None),
            Recommendation.dismissed_at.is_(None),
        )
        .order_by(Recommendation.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def list_for_scheduled(
    session: AsyncSession, user: User, scheduled_workout_id: UUID
) -> list[Recommendation]:
    stmt = (
        select(Recommendation)
        .where(
            Recommendation.user_id == user.id,
            Recommendation.scheduled_workout_id == scheduled_workout_id,
        )
        .order_by(Recommendation.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def _owned(session: AsyncSession, user: User, rec_id: UUID) -> Recommendation:
    record = (
        await session.execute(
            select(Recommendation).where(
                Recommendation.id == rec_id,
                Recommendation.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Recommendation not found.")
    return record


async def consume(session: AsyncSession, user: User, rec_id: UUID) -> Recommendation:
    record = await _owned(session, user, rec_id)
    if record.consumed_at is None:
        record.consumed_at = _now()
    await session.flush()
    return record


async def dismiss(session: AsyncSession, user: User, rec_id: UUID) -> Recommendation:
    record = await _owned(session, user, rec_id)
    if record.dismissed_at is None:
        record.dismissed_at = _now()
    await session.flush()
    return record
