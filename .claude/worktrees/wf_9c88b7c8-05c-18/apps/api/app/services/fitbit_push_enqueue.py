"""Best-effort enqueue for fitbit_push_session_task. Tests reassign these
functions to run inline so the push runs synchronously.
"""

from __future__ import annotations

import logging
from uuid import UUID

from arq.connections import ArqRedis, RedisSettings, create_pool

from app.config import get_settings

PUSH_TASK_NAME = "fitbit_push_session_task"


async def _create_pool() -> ArqRedis:
    return await create_pool(RedisSettings.from_dsn(get_settings().redis_url))


async def enqueue_push(session_id: UUID) -> None:
    log = logging.getLogger(__name__)
    try:
        redis = await _create_pool()
        try:
            await redis.enqueue_job(
                PUSH_TASK_NAME, str(session_id), _job_id=f"fitbit-push:{session_id}"
            )
        finally:
            await redis.close(close_connection_pool=True)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "fitbit_push_enqueue_failed",
            extra={"session_id": str(session_id), "error": repr(exc)},
        )
