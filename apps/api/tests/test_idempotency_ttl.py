"""Tests for the idempotency-key TTL sweep (API-9).

Seeds an 8-day-old key and a fresh key, runs the daily prune, and asserts
only the stale row is dropped.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from app.db import get_sessionmaker
from app.models.idempotency_key import IdempotencyKey
from app.models.user import User
from app.services import idempotency as idempotency_service
from app.workers.main import prune_idempotency_keys_daily


async def _make_user(session) -> UUID:
    user = User(email="ttl@example.com", display_name="TTL Tester")
    session.add(user)
    await session.flush()
    return user.id


async def _insert_key(session, user_id: UUID, key: str, *, age_days: float) -> UUID:
    record = IdempotencyKey(
        user_id=user_id,
        key=key,
        route="/v1/test",
        request_hash="deadbeef",
        response_status=200,
        response_body={"ok": True},
        created_at=datetime.now(tz=UTC) - timedelta(days=age_days),
    )
    session.add(record)
    await session.flush()
    return record.id


async def test_prune_drops_only_keys_older_than_retention() -> None:
    sm = get_sessionmaker()
    async with sm() as session:
        user_id = await _make_user(session)
        old_id = await _insert_key(session, user_id, "old-key", age_days=8)
        fresh_id = await _insert_key(session, user_id, "fresh-key", age_days=1)
        await session.commit()

    deleted = await prune_idempotency_keys_daily({})
    assert deleted == 1

    sm = get_sessionmaker()
    async with sm() as session:
        remaining = (await session.execute(select(IdempotencyKey.id))).scalars().all()
    assert old_id not in remaining
    assert fresh_id in remaining


async def test_prune_expired_respects_custom_retention_window() -> None:
    sm = get_sessionmaker()
    async with sm() as session:
        user_id = await _make_user(session)
        await _insert_key(session, user_id, "five-day", age_days=5)
        await _insert_key(session, user_id, "ten-day", age_days=10)
        await session.commit()

    sm = get_sessionmaker()
    async with sm() as session:
        # Retain only 7 days: the 10-day key goes, the 5-day key stays.
        deleted = await idempotency_service.prune_expired(session, retention_days=7)
        await session.commit()
    assert deleted == 1

    sm = get_sessionmaker()
    async with sm() as session:
        keys = (await session.execute(select(IdempotencyKey.key))).scalars().all()
    assert "five-day" in keys
    assert "ten-day" not in keys
