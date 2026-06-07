from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from arq.connections import RedisSettings
from arq.cron import cron

from app.config import get_settings
from app.db import get_sessionmaker
from app.logging_config import configure_logging, get_logger
from app.observability.spans import traced_arq_job
from app.services import fitbit_push as fitbit_push_service
from app.services import fitbit_sync as fitbit_sync_service
from app.services import idempotency as idempotency_service
from app.services import readiness as readiness_service
from app.services.ai.rationale_job import (
    rationalize_recommendation as _rationalize_recommendation,
)
from app.services.analytics import insights as insights_service
from app.services.analytics import volume as volume_service
from app.services.scheduling import enqueue_workout_reminders
from app.services.soft_delete_gc import purge_soft_deleted

# Wrap the imported rationale job so it gets an `arq.rationalize_recommendation`
# span like the locally-defined jobs. functools.wraps preserves __qualname__,
# which arq uses to register the job.
rationalize_recommendation = traced_arq_job(_rationalize_recommendation)


@traced_arq_job
async def healthcheck(_ctx: dict[str, Any]) -> str:
    log = get_logger("worker")
    log.info("worker_healthcheck")
    return "ok"


@traced_arq_job
async def workout_reminders(_ctx: dict[str, Any]) -> int:
    """Cron task: every hour, insert workout-reminder notifications for users
    whose local time is currently 06:00."""
    sm = get_sessionmaker()
    async with sm() as session:
        inserted = await enqueue_workout_reminders(session)
        await session.commit()
    get_logger("worker").info("workout_reminders_inserted", count=inserted)
    return inserted


@traced_arq_job
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


@traced_arq_job
async def rollup_yesterday_nightly(_ctx: dict[str, Any]) -> int:
    """Cron task: roll up every active user's week containing yesterday."""
    sm = get_sessionmaker()
    yesterday = (datetime.now(tz=UTC) - timedelta(days=1)).date()
    async with sm() as session:
        count = await volume_service.rollup_all_users_active_week(session, yesterday)
        await session.commit()
    get_logger("worker").info("rollup_yesterday_done", count=count)
    return count


@traced_arq_job
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


@traced_arq_job
async def fitbit_sync_user_task(_ctx: dict[str, Any], user_id: str) -> int:
    """Sync one user's Fitbit data. Idempotent."""
    sm = get_sessionmaker()
    async with sm() as session:
        result = await fitbit_sync_service.sync_user(session, UUID(user_id))
        await session.commit()
    get_logger("worker").info(
        "fitbit_sync_done",
        user_id=user_id,
        activities=result.activities_written,
        daily_metrics=result.daily_metrics_written,
    )
    return result.activities_written + result.daily_metrics_written


@traced_arq_job
async def fitbit_push_session_task(_ctx: dict[str, Any], session_id: str) -> dict[str, Any]:
    """Push one workout session to Fitbit. Idempotent."""
    sm = get_sessionmaker()
    async with sm() as session:
        result = await fitbit_push_service.push_session_to_fitbit(session, UUID(session_id))
        await session.commit()
    get_logger("worker").info(
        "fitbit_push_done",
        session_id=session_id,
        pushed=result.pushed,
        skipped_reason=result.skipped_reason,
        fitbit_log_id=result.fitbit_log_id,
    )
    return {
        "pushed": result.pushed,
        "skipped_reason": result.skipped_reason,
        "fitbit_log_id": result.fitbit_log_id,
    }


@traced_arq_job
async def compute_readiness_user_day_task(
    _ctx: dict[str, Any], user_id: str, target_iso_date: str
) -> int | None:
    """Reactive recompute for one user-day."""
    from datetime import date as _date

    sm = get_sessionmaker()
    async with sm() as session:
        result = await readiness_service.recompute_for_user_date(
            session, UUID(user_id), target_date=_date.fromisoformat(target_iso_date)
        )
        await session.commit()
    return result.score if result is not None else None


@traced_arq_job
async def compute_readiness_nightly(_ctx: dict[str, Any]) -> int:
    """Cron task: recompute readiness for every user with daily_metrics. Runs
    at 04:00 UTC. Uses the last 14 days so HRV backfills are picked up.
    """
    from sqlalchemy import select as _select

    from app.models.daily_metric import DailyMetric

    sm = get_sessionmaker()
    async with sm() as session:
        user_ids = (await session.execute(_select(DailyMetric.user_id).distinct())).scalars().all()
        total = 0
        for user_id in user_ids:
            try:
                results = await readiness_service.recompute_recent_for_user(session, user_id)
                total += len(results)
            except Exception as exc:  # noqa: BLE001
                get_logger("worker").warning(
                    "readiness_user_failed",
                    user_id=str(user_id),
                    error=repr(exc),
                )
        await session.commit()
    get_logger("worker").info("readiness_nightly_done", days_recomputed=total)
    return total


@traced_arq_job
async def fitbit_sync_all_periodic(_ctx: dict[str, Any]) -> int:
    """Cron task: sync every connected Fitbit user. Runs every 30 minutes."""
    from sqlalchemy import select as _select

    from app.models.fitbit_connection import FitbitConnection

    sm = get_sessionmaker()
    async with sm() as session:
        connections = (await session.execute(_select(FitbitConnection))).scalars().all()
        total = 0
        for connection in connections:
            try:
                result = await fitbit_sync_service.sync_user(session, connection.user_id)
                total += result.activities_written + result.daily_metrics_written
            except Exception as exc:  # noqa: BLE001
                get_logger("worker").warning(
                    "fitbit_sync_user_failed",
                    user_id=str(connection.user_id),
                    error=repr(exc),
                )
        await session.commit()
    get_logger("worker").info("fitbit_sync_all_done", total=total)
    return total


async def health_sync_all_periodic(_ctx: dict[str, Any]) -> int:
    """Cron task: sync body measurements (weight, body-fat) from Google Health
    for every connected user. Runs every 30 minutes."""
    from sqlalchemy import select as _select

    from app.models.fitbit_connection import FitbitConnection
    from app.services import health_sync as health_sync_service

    sm = get_sessionmaker()
    async with sm() as session:
        connections = (await session.execute(_select(FitbitConnection))).scalars().all()
        total = 0
        for connection in connections:
            try:
                result = await health_sync_service.sync_user(session, connection.user_id)
                total += (
                    result.weight_written + result.body_fat_written + result.daily_metrics_written
                )
            except Exception as exc:  # noqa: BLE001
                get_logger("worker").warning(
                    "health_sync_user_failed",
                    user_id=str(connection.user_id),
                    error=repr(exc),
                )
        await session.commit()
    get_logger("worker").info("health_sync_all_done", total=total)
    return total


@traced_arq_job
async def recompute_insights_nightly(_ctx: dict[str, Any]) -> int:
    """Cron task: recompute insights for every user, runs after the rollup.

    Also expires stale STAGNATION insights (30-day TTL for heuristic-only rows;
    LLM-rationale rows are kept far longer since regenerating them costs Ollama)
    so the analytics_insights table stays bounded.
    """
    from app.models.user import User

    sm = get_sessionmaker()
    async with sm() as session:
        from sqlalchemy import select as _select

        deleted = await insights_service.cleanup_expired_insights(session)
        users = (await session.execute(_select(User))).scalars().all()
        total = 0
        for user in users:
            ids = await insights_service.compute_insights_for_user(session, user)
            total += len(ids)
        await session.commit()
    get_logger("worker").info("recompute_insights_nightly_done", total=total, expired=deleted)
    return total


async def purge_soft_deleted_nightly(_ctx: dict[str, Any]) -> int:
    """Cron task: hard-delete soft-deleted workout_sessions, programs, and meals
    whose deleted_at is older than the retention window. Runs nightly at 03:00
    UTC (between the 02:15 insights cron and the 04:00 readiness cron)."""
    sm = get_sessionmaker()
    async with sm() as session:
        result = await purge_soft_deleted(session)
        await session.commit()
    get_logger("worker").info(
        "purge_soft_deleted_done",
        total=result.total,
        purged_by_table=result.purged_by_table,
    )
    return result.total


async def prune_idempotency_keys_daily(_ctx: dict[str, Any]) -> int:
    """Cron task: drop idempotency keys older than the retention window.

    The idempotency_keys table grows monotonically (the per-read lazy expiry
    only fires when a key is retried). This daily sweep bounds it. Runs at
    03:30 UTC, off the rollup/insights/readiness crons.
    """
    sm = get_sessionmaker()
    async with sm() as session:
        deleted = await idempotency_service.prune_expired(session)
        await session.commit()
    get_logger("worker").info("prune_idempotency_keys_done", deleted=deleted)
    return deleted


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
        fitbit_sync_user_task,
        fitbit_sync_all_periodic,
        health_sync_all_periodic,
        fitbit_push_session_task,
        compute_readiness_user_day_task,
        compute_readiness_nightly,
        purge_soft_deleted_nightly,
        prune_idempotency_keys_daily,
    ]
    cron_jobs = [
        # Every hour on the hour; per-user-tz dispatch happens inside the task.
        cron(workout_reminders, minute=0),  # type: ignore[arg-type]
        # Nightly at 02:00 UTC.
        cron(rollup_yesterday_nightly, hour=2, minute=0),  # type: ignore[arg-type]
        # Insights: 02:15 UTC, right after the rollup.
        cron(recompute_insights_nightly, hour=2, minute=15),  # type: ignore[arg-type]
        # Fitbit polling sync every 30 minutes (00 and 30).
        cron(fitbit_sync_all_periodic, minute={0, 30}),  # type: ignore[arg-type]
        # Google Health body-measurement sync every 30 minutes (15 and 45),
        # offset from the Fitbit pass so the two don't collide.
        cron(health_sync_all_periodic, minute={15, 45}),  # type: ignore[arg-type]
        # Readiness nightly at 04:00 UTC (after the rollup + insights crons).
        cron(compute_readiness_nightly, hour=4, minute=0),  # type: ignore[arg-type]
        # Soft-delete GC nightly at 03:00 UTC (clear of 02:00/02:15/04:00 crons).
        cron(purge_soft_deleted_nightly, hour=3, minute=0),  # type: ignore[arg-type]
        # Idempotency-key TTL sweep, daily at 03:30 UTC.
        cron(prune_idempotency_keys_daily, hour=3, minute=30),  # type: ignore[arg-type]
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings()
