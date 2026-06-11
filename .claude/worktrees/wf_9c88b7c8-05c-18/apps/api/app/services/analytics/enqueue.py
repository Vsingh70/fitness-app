"""Best-effort enqueue helpers for analytics rollup jobs. Tests reassign these
to run inline so the table is populated synchronously.
"""

from __future__ import annotations

import logging
from uuid import UUID

from arq.connections import ArqRedis, RedisSettings, create_pool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.scheduled_workout import ScheduledWorkout
from app.models.workout import WorkoutExercise, WorkoutSession, WorkoutSet

ROLLUP_TASK_NAME = "rollup_user_week_task"


async def _create_pool() -> ArqRedis:
    return await create_pool(RedisSettings.from_dsn(get_settings().redis_url))


async def enqueue_rollup(user_id: UUID, iso_year: int, iso_week: int) -> None:
    """Best-effort: a Redis outage logs and continues. The nightly job will
    pick up the stale week next cycle anyway.
    """
    log = logging.getLogger(__name__)
    try:
        redis = await _create_pool()
        try:
            # Dedup window: any pending job for the same (user, year, week)
            # within 60s collapses into one execution.
            job_id = f"rollup:{user_id}:{iso_year}:{iso_week}"
            await redis.enqueue_job(
                ROLLUP_TASK_NAME,
                str(user_id),
                iso_year,
                iso_week,
                _job_id=job_id,
                _defer_by=0,
            )
        finally:
            await redis.close(close_connection_pool=True)
    except Exception as exc:
        log.warning(
            "rollup_enqueue_failed",
            extra={
                "user_id": str(user_id),
                "iso_year": iso_year,
                "iso_week": iso_week,
                "error": repr(exc),
            },
        )


async def enqueue_rollup_for_set(session: AsyncSession, set_id: UUID) -> None:
    """If a set belongs to a finished session, enqueue a rollup for the
    session's ISO week. No-op when the session is still in progress (the
    finish endpoint will roll up).
    """
    row = (
        await session.execute(
            select(
                WorkoutSession.id,
                WorkoutSession.user_id,
                WorkoutSession.started_at,
                WorkoutSession.ended_at,
                ScheduledWorkout.scheduled_for,
            )
            .join(WorkoutExercise, WorkoutExercise.workout_session_id == WorkoutSession.id)
            .join(WorkoutSet, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
            .outerjoin(ScheduledWorkout, ScheduledWorkout.id == WorkoutSession.scheduled_workout_id)
            .where(WorkoutSet.id == set_id)
        )
    ).first()
    if row is None:
        return
    _, user_id, started_at, ended_at, scheduled_for = row
    if ended_at is None:
        return
    anchor = scheduled_for if scheduled_for is not None else started_at.date()
    iso_year, iso_week, _ = anchor.isocalendar()
    await enqueue_rollup(user_id, iso_year, iso_week)


async def enqueue_rollup_for_session(session: AsyncSession, session_id: UUID) -> None:
    """Enqueue when a session-level edit (e.g., delete/restore) happens after
    finish. Looks up the session, computes its ISO week, enqueues. No-op when
    not yet finished.
    """
    row = (
        await session.execute(
            select(
                WorkoutSession.user_id,
                WorkoutSession.started_at,
                WorkoutSession.ended_at,
                ScheduledWorkout.scheduled_for,
            )
            .outerjoin(ScheduledWorkout, ScheduledWorkout.id == WorkoutSession.scheduled_workout_id)
            .where(WorkoutSession.id == session_id)
        )
    ).first()
    if row is None:
        return
    user_id, started_at, ended_at, scheduled_for = row
    if ended_at is None:
        return
    anchor = scheduled_for if scheduled_for is not None else started_at.date()
    iso_year, iso_week, _ = anchor.isocalendar()
    await enqueue_rollup(user_id, iso_year, iso_week)
