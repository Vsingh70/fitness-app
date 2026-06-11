from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import ColumnElement, Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import Recommendation
from app.models.user import User
from app.services.pagination import decode_cursor, encode_cursor

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _cursor_clause(cursor: str | None) -> ColumnElement[bool] | None:
    """Keyset clause for (created_at desc, id desc) ordering."""
    decoded = decode_cursor(cursor)
    if decoded is None:
        return None
    try:
        cursor_created = datetime.fromisoformat(decoded["c"])
        cursor_id = UUID(decoded["i"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid cursor.") from exc
    return or_(
        Recommendation.created_at < cursor_created,
        and_(Recommendation.created_at == cursor_created, Recommendation.id < cursor_id),
    )


async def _paginate(
    session: AsyncSession, stmt: Select[tuple[Recommendation]], limit: int
) -> tuple[list[Recommendation], str | None]:
    rows = list((await session.execute(stmt)).scalars().all())
    next_cursor: str | None = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = encode_cursor({"c": last.created_at.isoformat(), "i": str(last.id)})
    return rows, next_cursor


async def list_active(
    session: AsyncSession,
    user: User,
    *,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> tuple[list[Recommendation], str | None]:
    limit = max(1, min(limit, MAX_LIMIT))
    stmt = (
        select(Recommendation)
        .where(
            Recommendation.user_id == user.id,
            Recommendation.consumed_at.is_(None),
            Recommendation.dismissed_at.is_(None),
        )
        .order_by(Recommendation.created_at.desc(), Recommendation.id.desc())
        .limit(limit + 1)
    )
    clause = _cursor_clause(cursor)
    if clause is not None:
        stmt = stmt.where(clause)
    return await _paginate(session, stmt, limit)


async def list_for_scheduled(
    session: AsyncSession,
    user: User,
    scheduled_workout_id: UUID,
    *,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> tuple[list[Recommendation], str | None]:
    limit = max(1, min(limit, MAX_LIMIT))
    stmt = (
        select(Recommendation)
        .where(
            Recommendation.user_id == user.id,
            Recommendation.scheduled_workout_id == scheduled_workout_id,
        )
        .order_by(Recommendation.created_at.desc(), Recommendation.id.desc())
        .limit(limit + 1)
    )
    clause = _cursor_clause(cursor)
    if clause is not None:
        stmt = stmt.where(clause)
    return await _paginate(session, stmt, limit)


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
