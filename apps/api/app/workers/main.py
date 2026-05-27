from typing import Any

from arq.connections import RedisSettings
from arq.cron import cron

from app.config import get_settings
from app.db import get_sessionmaker
from app.logging_config import configure_logging, get_logger
from app.services.ai.rationale_job import rationalize_recommendation
from app.services.scheduling import enqueue_workout_reminders


async def healthcheck(_ctx: dict[str, Any]) -> str:
    log = get_logger("worker")
    log.info("worker_healthcheck")
    return "ok"


async def workout_reminders(_ctx: dict[str, Any]) -> int:
    """Cron task: every hour, insert workout-reminder notifications for users
    whose local time is currently 06:00."""
    sm = get_sessionmaker()
    async with sm() as session:
        inserted = await enqueue_workout_reminders(session)
        await session.commit()
    get_logger("worker").info("workout_reminders_inserted", count=inserted)
    return inserted


async def startup(_ctx: dict[str, Any]) -> None:
    configure_logging()
    log = get_logger("worker")
    log.info("worker_started")


async def shutdown(_ctx: dict[str, Any]) -> None:
    get_logger("worker").info("worker_stopped")


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


class WorkerSettings:
    functions = [healthcheck, workout_reminders, rationalize_recommendation]
    cron_jobs = [
        # Every hour on the hour; per-user-tz dispatch happens inside the task.
        cron(workout_reminders, minute=0),  # type: ignore[arg-type]
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings()
