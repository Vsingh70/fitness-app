"""Test scaffolding for scheduled workouts.

The legacy week-based scheduler (``POST /programs/{id}/activate`` generating a
calendar of ``scheduled_workouts``) was removed with the flexible
microcycle/mesocycle model. ``scheduled_workouts`` rows are still written on
session start for history, but there is no longer an endpoint that
pre-generates a calendar.

Tests that exercise still-existing features (progression orchestration,
recommendations, analytics predictions, readiness deload, reminders, export,
GC) need a small set of planned ``scheduled_workouts`` to start sessions from.
This helper seeds them directly via the DB, decoupled from any program model
shape, so those features stay under test.
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select

from app.db import get_sessionmaker
from app.models.enums import ScheduledWorkoutStatus
from app.models.program import Program, ProgramDay
from app.models.scheduled_workout import ScheduledWorkout
from app.models.user import User


async def seed_scheduled_for_program(
    program_id: str | UUID,
    *,
    count: int,
    start: date | None = None,
    is_deload: list[bool] | None = None,
) -> list[str]:
    """Insert ``count`` planned ``scheduled_workouts`` for a program.

    Rows rotate through the program's *training* slots (rest slots are skipped)
    on consecutive days starting at ``start`` (defaults to today). Returns the
    created scheduled-workout ids in date order. ``is_deload`` may flag specific
    rows (defaults to all False).
    """
    start = start or date.today()
    sm = get_sessionmaker()
    async with sm() as session:
        program = (
            await session.execute(select(Program).where(Program.id == UUID(str(program_id))))
        ).scalar_one()
        user = (await session.execute(select(User).where(User.id == program.owner_id))).scalar_one()
        slots = (
            (
                await session.execute(
                    select(ProgramDay)
                    .where(
                        ProgramDay.program_id == program.id,
                        ProgramDay.is_rest_day.is_(False),
                    )
                    .order_by(ProgramDay.slot_index)
                )
            )
            .scalars()
            .all()
        )
        if not slots:
            raise ValueError("program has no training slots to schedule")

        ids: list[str] = []
        for i in range(count):
            slot = slots[i % len(slots)]
            row = ScheduledWorkout(
                user_id=user.id,
                program_id=program.id,
                program_day_id=slot.id,
                scheduled_for=start + timedelta(days=i),
                status=ScheduledWorkoutStatus.planned,
                microcycle_number=(i // len(slots)) + 1,
                repetition=1,
                is_deload=bool(is_deload[i]) if is_deload else False,
            )
            session.add(row)
            await session.flush()
            ids.append(str(row.id))
        await session.commit()
    return ids
