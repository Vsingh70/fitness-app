from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from arq.connections import RedisSettings
from arq.cron import cron

from app.config import get_settings
from app.db import get_sessionmaker
from app.logging_config import configure_logging, get_logger
from app.services.ai.rationale_job import rationalize_recommendation
from app.services.analytics import insights as insights_service
from app.services.analytics import volume as volume_service
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


async def rollup_user_week_task(
    _ctx: dict[str, Any], user_id: str, iso_year: int, iso_week: int
) -> int:
    """Reactive recompute: enqueued after a session is finished or edited."""
    sm = get_sessionmaker()
    async with sm() as session:
        written = await volume_service.rollup_user_week(session, UUID(user_id), iso_year, iso_week)
        await session.commit()
    get_logger("worker").info(
        "rollup_user_week_done",
        user_id=user_id,
        iso_year=iso_year,
        iso_week=iso_week,
        rows=written,
    )
    return written


async def rollup_yesterday_nightly(_ctx: dict[str, Any]) -> int:
    """Cron task: roll up every active user's week containing yesterday."""
    sm = get_sessionmaker()
    yesterday = (datetime.now(tz=UTC) - timedelta(days=1)).date()
    async with sm() as session:
        count = await volume_service.rollup_all_users_active_week(session, yesterday)
        await session.commit()
    get_logger("worker").info("rollup_yesterday_done", count=count)
    return count


async def recompute_insights_task(_ctx: dict[str, Any], user_id: str) -> int:
    """Reactive recompute: run all insight heuristics for one user."""
    from app.models.user import User

    sm = get_sessionmaker()
    async with sm() as session:
        from sqlalchemy import select as _select

        user = (
            await session.execute(_select(User).where(User.id == UUID(user_id)))
        ).scalar_one_or_none()
        if user is None:
            return 0
        ids = await insights_service.compute_insights_for_user(session, user)
        await session.commit()
    get_logger("worker").info("recompute_insights_done", user_id=user_id, count=len(ids))
    return len(ids)


async def recompute_insights_nightly(_ctx: dict[str, Any]) -> int:
    """Cron task: recompute insights for every user, runs after the rollup."""
    from app.models.user import User

    sm = get_sessionmaker()
    async with sm() as session:
        from sqlalchemy import select as _select

        users = (await session.execute(_select(User))).scalars().all()
        total = 0
        for user in users:
            ids = await insights_service.compute_insights_for_user(session, user)
            total += len(ids)
        await session.commit()
    get_logger("worker").info("recompute_insights_nightly_done", total=total)
    return total


async def startup(_ctx: dict[str, Any]) -> None:
    configure_logging()
    log = get_logger("worker")
    log.info("worker_started")


async def shutdown(_ctx: dict[str, Any]) -> None:
    get_logger("worker").info("worker_stopped")


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


class WorkerSettings:
    functions = [
        healthcheck,
        workout_reminders,
        rationalize_recommendation,
        rollup_user_week_task,
        rollup_yesterday_nightly,
        recompute_insights_task,
        recompute_insights_nightly,
    ]
    cron_jobs = [
        # Every hour on the hour; per-user-tz dispatch happens inside the task.
        cron(workout_reminders, minute=0),  # type: ignore[arg-type]
        # Nightly at 02:00 UTC.
        cron(rollup_yesterday_nightly, hour=2, minute=0),  # type: ignore[arg-type]
        # Insights: 02:15 UTC, right after the rollup.
        cron(recompute_insights_nightly, hour=2, minute=15),  # type: ignore[arg-type]
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings()
