"""Idempotency-Key cache scoped per (user_id, key, route).

Usage in a route:
    cached = await get_cached_idempotent(session, user_id, key, route, request_hash)
    if cached: return cached
    ... do work ...
    await save_idempotent(session, user_id, key, route, request_hash, status, body)

Entries expire after IDEMPOTENCY_TTL_SECONDS (lazy: stale rows are deleted on read).
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import CursorResult, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency_key import IdempotencyKey

IDEMPOTENCY_TTL_SECONDS = 24 * 60 * 60

# Hard retention backstop for the daily sweep. The per-read lazy expiry above
# only deletes a stale row when its key is read again; this window bounds the
# table for keys that are never retried.
IDEMPOTENCY_RETENTION_DAYS = 7


def hash_payload(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()


async def get_cached_idempotent(
    session: AsyncSession,
    user_id: UUID,
    key: str,
    route: str,
    request_hash: str,
) -> tuple[int, dict[str, Any] | None] | None:
    record = (
        await session.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.user_id == user_id,
                IdempotencyKey.key == key,
                IdempotencyKey.route == route,
            )
        )
    ).scalar_one_or_none()
    if record is None:
        return None

    age = datetime.now(tz=UTC) - record.created_at
    if age > timedelta(seconds=IDEMPOTENCY_TTL_SECONDS):
        await session.execute(delete(IdempotencyKey).where(IdempotencyKey.id == record.id))
        await session.commit()
        return None

    if record.request_hash != request_hash:
        raise HTTPException(
            status_code=409,
            detail="Idempotency-Key was reused with a different request body.",
        )
    return record.response_status, record.response_body


async def prune_expired(
    session: AsyncSession,
    *,
    retention_days: int = IDEMPOTENCY_RETENTION_DAYS,
) -> int:
    """Drop idempotency keys older than `retention_days`.

    Returns the number of rows deleted. Caller is responsible for committing.
    """
    cutoff = datetime.now(tz=UTC) - timedelta(days=retention_days)
    result = await session.execute(delete(IdempotencyKey).where(IdempotencyKey.created_at < cutoff))
    # A DELETE yields a CursorResult, which exposes rowcount; the base Result
    # type does not, so narrow it for the type checker.
    return cast("CursorResult[Any]", result).rowcount or 0


async def save_idempotent(
    session: AsyncSession,
    user_id: UUID,
    key: str,
    route: str,
    request_hash: str,
    response_status: int,
    response_body: dict[str, Any] | None,
) -> None:
    session.add(
        IdempotencyKey(
            user_id=user_id,
            key=key,
            route=route,
            request_hash=request_hash,
            response_status=response_status,
            response_body=response_body,
        )
    )
    await session.commit()
