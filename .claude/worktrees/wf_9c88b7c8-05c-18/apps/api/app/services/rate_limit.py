"""Endpoint-scoped rate limiters.

Two strategies in one module:

1. `RedisHourlyLimiter`: Redis INCR with EX for fixed-window per-user-hour
   caps. Used by AI endpoints (60/hour per user).
2. `VPSConcurrencyLimiter`: process-local asyncio.Semaphore with non-blocking
   acquire. Use as a context manager; raises HTTPException(429, "busy") if
   the cap is full.

Tests monkeypatch `_get_redis` to inject a fakeredis or a no-op limiter.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from fastapi import HTTPException

from app.config import get_settings

logger = logging.getLogger(__name__)

# 60 recognitions per user per hour.
PHOTO_RECOGNIZE_HOURLY_LIMIT = 60
PHOTO_RECOGNIZE_WINDOW_SECONDS = 3600
# 6 concurrent recognitions across the whole VPS.
PHOTO_RECOGNIZE_CONCURRENCY = 6


class RedisLike(Protocol):
    async def incr(self, key: str) -> int: ...
    async def expire(self, key: str, seconds: int) -> bool: ...
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


async def check_hourly_limit(
    user_id: UUID,
    *,
    key_namespace: str,
    limit: int,
    window_seconds: int = PHOTO_RECOGNIZE_WINDOW_SECONDS,
) -> None:
    """Fixed-window INCR+EX. Raises 429 with Retry-After when over limit."""
    import time

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


# ---------------------------------------------------------------------------
# Process-local concurrency cap
# ---------------------------------------------------------------------------


_photo_concurrency = asyncio.Semaphore(PHOTO_RECOGNIZE_CONCURRENCY)


def reset_concurrency_for_tests(value: int = PHOTO_RECOGNIZE_CONCURRENCY) -> None:
    global _photo_concurrency
    _photo_concurrency = asyncio.Semaphore(value)


@contextlib.asynccontextmanager
async def acquire_photo_slot() -> AsyncIterator[None]:
    """Acquire one of N VPS-wide photo recognition slots. Raises 429 if all
    slots are busy (non-blocking).
    """
    acquired = False
    try:
        # Non-blocking acquire: if locked, raise 429.
        if _photo_concurrency.locked():
            raise HTTPException(
                status_code=429,
                detail="busy",
                headers={"Retry-After": "5"},
            )
        await asyncio.wait_for(_photo_concurrency.acquire(), timeout=0.001)
        acquired = True
        yield
    except TimeoutError as exc:
        raise HTTPException(
            status_code=429,
            detail="busy",
            headers={"Retry-After": "5"},
        ) from exc
    finally:
        if acquired:
            _photo_concurrency.release()
