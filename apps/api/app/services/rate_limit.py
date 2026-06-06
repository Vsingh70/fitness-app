"""Endpoint-scoped rate limiters.

Three strategies in one module:

1. `check_sliding_window`: Redis sorted-set sliding window. Used for the global
   per-user cap (600/min) and per-IP auth cap (30/min). Each request adds a
   timestamped member to a ZSET, prunes anything older than the window, then
   counts the live members. Smoother than a fixed window: there is no burst at
   the window boundary.
2. `check_hourly_limit`: Redis INCR with EX for a fixed-window per-user-hour
   cap. Used by AI endpoints (60/hour per user).

Limits (see tasks/00-overview/api-conventions.md "Rate limits"):

- Global default: 600 req/min per user.
- Auth endpoints: 30 req/min per IP.
- AI endpoints (recommendations): 60 req/hour per user.
- 429 with `Retry-After` header on limit.

Tests monkeypatch `_get_redis` to inject a fakeredis or a no-op limiter.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Protocol
from uuid import UUID

from fastapi import HTTPException

from app.config import get_settings

logger = logging.getLogger(__name__)

# --- Spec ceilings (tasks/00-overview/api-conventions.md "Rate limits") ------

# Global default: 600 requests per minute per user.
USER_REQUESTS_PER_MINUTE_LIMIT = 600
USER_WINDOW_SECONDS = 60

# Auth endpoints: 30 requests per minute per IP.
AUTH_IP_REQUESTS_PER_MINUTE_LIMIT = 30
AUTH_IP_WINDOW_SECONDS = 60

# AI endpoints (recommendations): 60 requests per hour per user.
AI_REQUESTS_PER_HOUR_LIMIT = 60
AI_WINDOW_SECONDS = 3600


class RedisLike(Protocol):
    async def incr(self, key: str) -> int: ...
    async def expire(self, key: str, seconds: int) -> bool: ...
    async def zadd(self, key: str, mapping: dict[str, float]) -> int: ...
    async def zremrangebyscore(self, key: str, min: float, max: float) -> int: ...
    async def zcard(self, key: str) -> int: ...
    async def close(self) -> None: ...


_redis_singleton: RedisLike | None = None


async def _get_redis() -> RedisLike:
    """Lazy module-level Redis client. Tests monkeypatch this entire function."""
    global _redis_singleton
    if _redis_singleton is None:
        from redis.asyncio import Redis  # local import: optional dep at import time

        _redis_singleton = Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis_singleton


def reset_redis_for_tests() -> None:
    global _redis_singleton
    _redis_singleton = None


async def check_sliding_window(
    identity: str,
    *,
    key_namespace: str,
    limit: int,
    window_seconds: int,
) -> None:
    """Redis sorted-set sliding window. Raises 429 with Retry-After over limit.

    ``identity`` is whatever the limit is scoped to (a user id for the global
    per-user cap, a client IP for the per-IP auth cap). Each request is recorded
    as a unique ZSET member scored by its arrival time; expired members are
    pruned before the live count is compared against ``limit``.
    """
    try:
        redis = await _get_redis()
    except Exception as exc:
        logger.warning("rate_limit_redis_unavailable", extra={"error": repr(exc)})
        return  # fail-open: don't block users if Redis is down

    now = time.time()
    window_start = now - window_seconds
    key = f"rl:{key_namespace}:{identity}"
    # A unique member so concurrent requests in the same instant don't collide.
    member = f"{now:.6f}:{uuid.uuid4().hex}"
    try:
        await redis.zremrangebyscore(key, 0, window_start)
        await redis.zadd(key, {member: now})
        count = await redis.zcard(key)
        # Keep the key from leaking if the identity goes quiet.
        await redis.expire(key, window_seconds)
    except Exception as exc:
        logger.warning("rate_limit_zset_failed", extra={"error": repr(exc)})
        return

    if count > limit:
        raise HTTPException(
            status_code=429,
            detail="rate_limited",
            headers={"Retry-After": str(window_seconds)},
        )


async def check_user_limit(user_id: UUID) -> None:
    """Global default cap: 600 req/min per user (sliding window)."""
    await check_sliding_window(
        str(user_id),
        key_namespace="user",
        limit=USER_REQUESTS_PER_MINUTE_LIMIT,
        window_seconds=USER_WINDOW_SECONDS,
    )


async def check_auth_ip_limit(client_ip: str) -> None:
    """Auth endpoint cap: 30 req/min per IP (sliding window)."""
    await check_sliding_window(
        client_ip,
        key_namespace="auth_ip",
        limit=AUTH_IP_REQUESTS_PER_MINUTE_LIMIT,
        window_seconds=AUTH_IP_WINDOW_SECONDS,
    )


async def check_hourly_limit(
    user_id: UUID,
    *,
    key_namespace: str,
    limit: int,
    window_seconds: int = AI_WINDOW_SECONDS,
) -> None:
    """Fixed-window INCR+EX. Raises 429 with Retry-After when over limit."""
    try:
        redis = await _get_redis()
    except Exception as exc:
        logger.warning("rate_limit_redis_unavailable", extra={"error": repr(exc)})
        return  # fail-open: don't block users if Redis is down

    now = int(time.time())
    window_start = (now // window_seconds) * window_seconds
    key = f"rl:{key_namespace}:{user_id}:{window_start}"
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
    except Exception as exc:
        logger.warning("rate_limit_incr_failed", extra={"error": repr(exc)})
        return

    if count > limit:
        retry_after = window_start + window_seconds - now
        raise HTTPException(
            status_code=429,
            detail="rate_limited",
            headers={"Retry-After": str(max(1, retry_after))},
        )
