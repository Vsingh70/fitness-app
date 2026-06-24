from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationKind, ScheduledWorkoutStatus
from app.models.notification import Notification
from app.models.program import Program, ProgramDay, ProgramDayExercise
from app.models.scheduled_workout import ScheduledWorkout
from app.models.user import User
from app.models.workout import WorkoutExercise, WorkoutSession
from app.schemas.scheduling import ScheduledWorkoutUpdate


def _now() -> datetime:
    return datetime.now(tz=UTC)


async def list_scheduled(
    session: AsyncSession,
    user: User,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[dict[str, Any]]:
    """Return scheduled workouts with embedded program-day metadata."""
    stmt = (
        select(
            ScheduledWorkout,
            ProgramDay.name.label("program_day_name"),
            Program.name.label("program_name"),
            func.count(ProgramDayExercise.id).label("exercise_count"),
        )
        .outerjoin(ProgramDay, ProgramDay.id == ScheduledWorkout.program_day_id)
        .outerjoin(Program, Program.id == ScheduledWorkout.program_id)
        .outerjoin(ProgramDayExercise, ProgramDayExercise.program_day_id == ProgramDay.id)
        .where(ScheduledWorkout.user_id == user.id)
        .group_by(ScheduledWorkout.id, ProgramDay.name, Program.name)
        .order_by(ScheduledWorkout.scheduled_for)
    )
    if from_date is not None:
        stmt = stmt.where(ScheduledWorkout.scheduled_for >= from_date)
    if to_date is not None:
        stmt = stmt.where(ScheduledWorkout.scheduled_for <= to_date)

    rows = (await session.execute(stmt)).all()
    out: list[dict[str, Any]] = []
    for sw, day_name, program_name, count in rows:
        out.append(
            {
                "id": sw.id,
                "program_id": sw.program_id,
                "program_day_id": sw.program_day_id,
                "scheduled_for": sw.scheduled_for,
                "status": sw.status,
                "microcycle_number": sw.microcycle_number,
                "repetition": sw.repetition,
                "is_deload": sw.is_deload,
                "program_day_name": day_name,
                "program_name": program_name,
                "exercise_count": int(count),
            }
        )
    return out


async def _owned_scheduled(
    session: AsyncSession, user: User, scheduled_id: UUID
) -> ScheduledWorkout:
    record = (
        await session.execute(
            select(ScheduledWorkout).where(
                ScheduledWorkout.id == scheduled_id,
                ScheduledWorkout.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Scheduled workout not found.")
    return record


async def update_scheduled(
    session: AsyncSession,
    user: User,
    scheduled_id: UUID,
    payload: ScheduledWorkoutUpdate,
    *,
    shift_remaining_days: int = 0,
) -> ScheduledWorkout:
    """Update one scheduled workout. If shift_remaining_days != 0 and the caller
    moved scheduled_for, every later scheduled workout in the same program is
    shifted by the same delta.
    """
    record = await _owned_scheduled(session, user, scheduled_id)
    original_date = record.scheduled_for

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(record, field, value)
    await session.flush()

    if shift_remaining_days and record.program_id is not None:
        await session.execute(
            update(ScheduledWorkout)
            .where(
                ScheduledWorkout.program_id == record.program_id,
                ScheduledWorkout.id != record.id,
                ScheduledWorkout.scheduled_for > original_date,
            )
            .values(
                scheduled_for=ScheduledWorkout.scheduled_for + timedelta(days=shift_remaining_days)
            )
        )
        await session.flush()
    return record


async def start_session_from_scheduled(
    session: AsyncSession, user: User, scheduled_id: UUID
) -> WorkoutSession:
    """Create a workout_session linked to the scheduled workout, pre-populated
    with workout_exercises copied from the program day.
    """
    scheduled = await _owned_scheduled(session, user, scheduled_id)
    if scheduled.status == ScheduledWorkoutStatus.completed:
        raise HTTPException(status_code=409, detail="Scheduled workout is already completed.")

    workout = WorkoutSession(
        user_id=user.id,
        scheduled_workout_id=scheduled.id,
        name=None,
    )
    session.add(workout)
    await session.flush()

    if scheduled.program_day_id is not None:
        program_exercises = (
            (
                await session.execute(
                    select(ProgramDayExercise)
                    .where(ProgramDayExercise.program_day_id == scheduled.program_day_id)
                    .order_by(ProgramDayExercise.position)
                )
            )
            .scalars()
            .all()
        )
        for pde in program_exercises:
            session.add(
                WorkoutExercise(
                    workout_session_id=workout.id,
                    exercise_id=pde.exercise_id,
                    position=pde.position,
                    notes=pde.notes,
                )
            )

    scheduled.status = ScheduledWorkoutStatus.in_progress
    await session.flush()
    return workout


async def mark_scheduled_completed_for_session(
    session: AsyncSession, scheduled_workout_id: UUID
) -> None:
    record = (
        await session.execute(
            select(ScheduledWorkout).where(ScheduledWorkout.id == scheduled_workout_id)
        )
    ).scalar_one_or_none()
    if record is None:
        return
    record.status = ScheduledWorkoutStatus.completed
    await session.flush()


# ---------------------------------------------------------------------------
# Background reminder job
# ---------------------------------------------------------------------------


def _is_six_am_in_tz(now_utc: datetime, tz_name: str) -> bool:
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        return False
    local = now_utc.astimezone(tz)
    return local.hour == 6


async def enqueue_workout_reminders(
    session: AsyncSession, *, now_utc: datetime | None = None
) -> int:
    """For every user where it's currently 06:00 local, insert workout-reminder
    notifications for that day's planned scheduled workouts.

    Idempotent within the same hour: if a notification with the same
    (user_id, kind, scheduled_for) was already inserted today, skip.
    """
    now_utc = now_utc or _now()
    users = (await session.execute(select(User))).scalars().all()
    inserted = 0
    for user in users:
        if not _is_six_am_in_tz(now_utc, user.timezone):
            continue
        try:
            tz = ZoneInfo(user.timezone)
        except Exception:
            continue
        local_today = now_utc.astimezone(tz).date()
        planned = (
            (
                await session.execute(
                    select(ScheduledWorkout).where(
                        ScheduledWorkout.user_id == user.id,
                        ScheduledWorkout.scheduled_for == local_today,
                        ScheduledWorkout.status == ScheduledWorkoutStatus.planned,
                    )
                )
            )
            .scalars()
            .all()
        )
        if not planned:
            continue

        local_six_am = datetime.combine(local_today, time(6, 0), tzinfo=tz)
        existing = (
            await session.execute(
                select(Notification.id).where(
                    Notification.user_id == user.id,
                    Notification.kind == NotificationKind.workout_reminder,
                    Notification.scheduled_for == local_six_am,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            continue

        session.add(
            Notification(
                user_id=user.id,
                kind=NotificationKind.workout_reminder,
                payload={
                    "scheduled_workout_ids": [str(p.id) for p in planned],
                    "date": local_today.isoformat(),
                },
                scheduled_for=local_six_am,
            )
        )
        inserted += 1
    if inserted > 0:
        await session.flush()
    return inserted
