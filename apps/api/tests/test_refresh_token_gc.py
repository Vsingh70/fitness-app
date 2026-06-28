"""Tests for the nightly refresh-token garbage-collection job.

Seeds tokens across the relevant states (expired long ago, revoked long ago,
expired recently, revoked recently, live) and asserts the purge deletes only the
dead-and-old ones and bumps the Prometheus counter.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from uuid6 import uuid7

from app.db import get_sessionmaker
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.observability.metrics import REFRESH_TOKENS_PURGED_TOTAL
from app.services.refresh_token_gc import purge_expired_refresh_tokens

RETENTION_DAYS = 30


def _counter_value() -> float:
    for metric in REFRESH_TOKENS_PURGED_TOTAL.collect():
        for sample in metric.samples:
            if sample.name.endswith("_total"):
                return sample.value
    return 0.0


async def _make_user(session) -> UUID:
    user = User(email="rtgc@example.com", apple_sub="rtgc-sub")
    session.add(user)
    await session.flush()
    return user.id


def _token(
    user_id: UUID,
    *,
    label: str,
    expires_at: datetime,
    revoked_at: datetime | None = None,
) -> RefreshToken:
    tid = uuid7()
    return RefreshToken(
        id=tid,
        user_id=user_id,
        token_hash=f"hash-{label}",
        expires_at=expires_at,
        revoked_at=revoked_at,
        family_id=tid,
    )


async def test_purge_removes_dead_tokens_and_spares_live_or_recent() -> None:
    now = datetime.now(tz=UTC)
    old = now - timedelta(days=RETENTION_DAYS + 5)
    recent = now - timedelta(days=RETENTION_DAYS - 5)
    future = now + timedelta(days=30)

    sm = get_sessionmaker()
    async with sm() as session:
        user_id = await _make_user(session)
        session.add_all(
            [
                _token(user_id, label="expired-old", expires_at=old),
                _token(user_id, label="revoked-old", expires_at=future, revoked_at=old),
                _token(user_id, label="expired-recent", expires_at=recent),
                _token(user_id, label="revoked-recent", expires_at=future, revoked_at=recent),
                _token(user_id, label="live", expires_at=future),
            ]
        )
        await session.commit()

        before = _counter_value()
        purged = await purge_expired_refresh_tokens(session, now=now, retention_days=RETENTION_DAYS)
        await session.commit()

        # Only the expired-long-ago and revoked-long-ago tokens are deleted.
        assert purged == 2
        remaining = (await session.execute(select(func.count()).select_from(RefreshToken))).scalar()
        assert remaining == 3
        assert _counter_value() == before + 2


async def test_purge_is_noop_without_dead_tokens() -> None:
    now = datetime.now(tz=UTC)
    sm = get_sessionmaker()
    async with sm() as session:
        user_id = await _make_user(session)
        session.add(_token(user_id, label="live", expires_at=now + timedelta(days=30)))
        await session.commit()

        purged = await purge_expired_refresh_tokens(session, now=now, retention_days=RETENTION_DAYS)
        await session.commit()

        assert purged == 0
        remaining = (await session.execute(select(func.count()).select_from(RefreshToken))).scalar()
        assert remaining == 1
