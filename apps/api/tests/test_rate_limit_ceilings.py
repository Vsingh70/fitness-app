"""Boundary tests for the spec's three rate-limit tiers.

Spec (tasks/00-overview/api-conventions.md "Rate limits"):

- Global default: 600 req/min per user.
- Auth endpoints: 30 req/min per IP.
- AI endpoints (recommendations, photo recognition): 60 req/hour per user.

Each tier is exercised at its boundary: the first N requests pass and the
(N+1)th is blocked with 429 + Retry-After. A tiny in-memory fake Redis stands
in for the real client (the production code monkeypatches `_get_redis`).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services import rate_limit


class _FakeRedis:
    """Minimal in-memory Redis supporting the ops both limiters need.

    - INCR/EXPIRE for the fixed-window (AI hourly) limiter.
    - ZADD/ZREMRANGEBYSCORE/ZCARD/EXPIRE for the sliding-window limiters.
    """

    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.zsets: dict[str, dict[str, float]] = {}

    async def incr(self, key: str) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    async def expire(self, key: str, seconds: int) -> bool:
        return True

    async def zadd(self, key: str, mapping: dict[str, float]) -> int:
        zset = self.zsets.setdefault(key, {})
        added = sum(1 for m in mapping if m not in zset)
        zset.update(mapping)
        return added

    async def zremrangebyscore(self, key: str, min: float, max: float) -> int:
        zset = self.zsets.get(key, {})
        to_drop = [m for m, score in zset.items() if min <= score <= max]
        for m in to_drop:
            del zset[m]
        return len(to_drop)

    async def zcard(self, key: str) -> int:
        return len(self.zsets.get(key, {}))

    async def close(self) -> None:
        return None


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> _FakeRedis:
    redis = _FakeRedis()

    async def _get() -> _FakeRedis:
        return redis

    monkeypatch.setattr(rate_limit, "_get_redis", _get)
    return redis


# ---------------------------------------------------------------------------
# Spec ceilings match the contract
# ---------------------------------------------------------------------------


def test_ceilings_match_spec() -> None:
    assert rate_limit.USER_REQUESTS_PER_MINUTE_LIMIT == 600
    assert rate_limit.USER_WINDOW_SECONDS == 60
    assert rate_limit.AUTH_IP_REQUESTS_PER_MINUTE_LIMIT == 30
    assert rate_limit.AUTH_IP_WINDOW_SECONDS == 60
    assert rate_limit.AI_REQUESTS_PER_HOUR_LIMIT == 60
    assert rate_limit.AI_WINDOW_SECONDS == 3600
    # The photo-recognition AI endpoint reuses the AI hourly ceiling.
    assert rate_limit.PHOTO_RECOGNIZE_HOURLY_LIMIT == 60
    assert rate_limit.PHOTO_RECOGNIZE_WINDOW_SECONDS == 3600


# ---------------------------------------------------------------------------
# Tier 1: global 600/min per user (sliding window)
# ---------------------------------------------------------------------------


async def test_user_tier_blocks_n_plus_one(fake_redis: _FakeRedis) -> None:
    user_id = uuid4()
    limit = rate_limit.USER_REQUESTS_PER_MINUTE_LIMIT

    # First `limit` requests are allowed.
    for _ in range(limit):
        await rate_limit.check_user_limit(user_id)

    # The (N+1)th request is blocked.
    with pytest.raises(HTTPException) as exc_info:
        await rate_limit.check_user_limit(user_id)
    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == "rate_limited"
    assert exc_info.value.headers is not None
    assert exc_info.value.headers["Retry-After"] == str(rate_limit.USER_WINDOW_SECONDS)


async def test_user_tier_is_per_user(fake_redis: _FakeRedis) -> None:
    """One user hitting the ceiling must not block a different user."""
    hot_user = uuid4()
    for _ in range(rate_limit.USER_REQUESTS_PER_MINUTE_LIMIT):
        await rate_limit.check_user_limit(hot_user)
    with pytest.raises(HTTPException):
        await rate_limit.check_user_limit(hot_user)

    # A fresh user still gets through.
    await rate_limit.check_user_limit(uuid4())


# ---------------------------------------------------------------------------
# Tier 2: auth 30/min per IP (sliding window)
# ---------------------------------------------------------------------------


async def test_auth_ip_tier_blocks_n_plus_one(fake_redis: _FakeRedis) -> None:
    ip = "203.0.113.7"
    limit = rate_limit.AUTH_IP_REQUESTS_PER_MINUTE_LIMIT

    for _ in range(limit):
        await rate_limit.check_auth_ip_limit(ip)

    with pytest.raises(HTTPException) as exc_info:
        await rate_limit.check_auth_ip_limit(ip)
    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == "rate_limited"
    assert exc_info.value.headers is not None
    assert exc_info.value.headers["Retry-After"] == str(rate_limit.AUTH_IP_WINDOW_SECONDS)


async def test_auth_ip_tier_is_per_ip(fake_redis: _FakeRedis) -> None:
    hot_ip = "203.0.113.7"
    for _ in range(rate_limit.AUTH_IP_REQUESTS_PER_MINUTE_LIMIT):
        await rate_limit.check_auth_ip_limit(hot_ip)
    with pytest.raises(HTTPException):
        await rate_limit.check_auth_ip_limit(hot_ip)

    # A different IP is unaffected.
    await rate_limit.check_auth_ip_limit("198.51.100.42")


# ---------------------------------------------------------------------------
# Tier 3: AI 60/hour per user (fixed window)
# ---------------------------------------------------------------------------


async def test_ai_tier_blocks_n_plus_one(fake_redis: _FakeRedis) -> None:
    user_id = uuid4()
    limit = rate_limit.AI_REQUESTS_PER_HOUR_LIMIT

    for _ in range(limit):
        await rate_limit.check_hourly_limit(
            user_id,
            key_namespace="ai",
            limit=limit,
            window_seconds=rate_limit.AI_WINDOW_SECONDS,
        )

    with pytest.raises(HTTPException) as exc_info:
        await rate_limit.check_hourly_limit(
            user_id,
            key_namespace="ai",
            limit=limit,
            window_seconds=rate_limit.AI_WINDOW_SECONDS,
        )
    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == "rate_limited"
    assert exc_info.value.headers is not None
    assert int(exc_info.value.headers["Retry-After"]) >= 1


async def test_ai_tier_is_per_user(fake_redis: _FakeRedis) -> None:
    hot_user = uuid4()
    limit = rate_limit.AI_REQUESTS_PER_HOUR_LIMIT
    for _ in range(limit):
        await rate_limit.check_hourly_limit(
            hot_user, key_namespace="ai", limit=limit, window_seconds=rate_limit.AI_WINDOW_SECONDS
        )
    with pytest.raises(HTTPException):
        await rate_limit.check_hourly_limit(
            hot_user, key_namespace="ai", limit=limit, window_seconds=rate_limit.AI_WINDOW_SECONDS
        )

    # A fresh user still gets through.
    await rate_limit.check_hourly_limit(
        uuid4(), key_namespace="ai", limit=limit, window_seconds=rate_limit.AI_WINDOW_SECONDS
    )


# ---------------------------------------------------------------------------
# Fail-open: a dead Redis must never block requests.
# ---------------------------------------------------------------------------


async def test_sliding_window_fails_open(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _boom() -> rate_limit.RedisLike:
        raise ConnectionError("redis down")

    monkeypatch.setattr(rate_limit, "_get_redis", _boom)

    # Far past any ceiling; must not raise because Redis is unreachable.
    for _ in range(rate_limit.USER_REQUESTS_PER_MINUTE_LIMIT + 5):
        await rate_limit.check_user_limit(uuid4())
