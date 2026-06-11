"""Best-effort enqueue for Fitbit sync jobs. Tests reassign this module's
functions to run inline so the sync runs synchronously.
"""

from __future__ import annotations

import logging
from uuid import UUID

from arq.connections import ArqRedis, RedisSettings, create_pool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_sessionmaker
from app.models.fitbit_connection import FitbitConnection

SYNC_TASK_NAME = "fitbit_sync_user_task"


async def _create_pool() -> ArqRedis:
    return await create_pool(RedisSettings.from_dsn(get_settings().redis_url))


async def enqueue_sync_for_user(user_id: UUID) -> None:
    log = logging.getLogger(__name__)
    try:
        redis = await _create_pool()
        try:
            await redis.enqueue_job(SYNC_TASK_NAME, str(user_id), _job_id=f"fitbit-sync:{user_id}")
        finally:
            await redis.close(close_connection_pool=True)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "fitbit_sync_enqueue_failed",
            extra={"user_id": str(user_id), "error": repr(exc)},
        )


async def _user_id_for_fitbit_user(session: AsyncSession, fitbit_user_id: str) -> UUID | None:
    row = (
        await session.execute(
            select(FitbitConnection.user_id).where(
                FitbitConnection.fitbit_user_id == fitbit_user_id
            )
        )
    ).first()
    return row[0] if row else None


async def enqueue_sync_for_fitbit_user(fitbit_user_id: str) -> None:
    """Look up our user_id from the Fitbit-side id and enqueue."""
    sm = get_sessionmaker()
    async with sm() as session:
        user_id = await _user_id_for_fitbit_user(session, fitbit_user_id)
    if user_id is None:
        return
    await enqueue_sync_for_user(user_id)
