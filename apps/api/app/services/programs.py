from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    ProgramGoal,
    ProgramSource,
    ProgressionStrategy,
    ScheduledWorkoutStatus,
)
from app.models.exercise import Exercise
from app.models.program import Program, ProgramDay, ProgramDayExercise, ProgramTemplate
from app.models.scheduled_workout import ScheduledWorkout
from app.models.user import User
from app.schemas.program import (
    ProgramCreate,
    ProgramDayCreate,
    ProgramDayExerciseCreate,
    ProgramDayExerciseUpdate,
    ProgramUpdate,
)
from app.services.progression.mesocycle import compute_mesocycle_position


def _now() -> datetime:
    return datetime.now(tz=UTC)


async def list_templates(session: AsyncSession) -> list[ProgramTemplate]:
    stmt = select(ProgramTemplate).order_by(ProgramTemplate.name)
    return list((await session.execute(stmt)).scalars().all())


async def get_template_by_slug(session: AsyncSession, slug: str) -> ProgramTemplate:
    record = (
        await session.execute(select(ProgramTemplate).where(ProgramTemplate.slug == slug))
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Program template not found.")
    return record


async def _disambiguate_name(session: AsyncSession, owner_id: UUID, base_name: str) -> str:
    """Append (2), (3), ... if the user already owns programs with this name."""
    existing = (
        (
            await session.execute(
                select(Program.name).where(
                    Program.owner_id == owner_id,
                    func.lower(Program.name).like(func.lower(base_name) + "%"),
                    Program.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    if base_name not in existing:
        return base_name
    suffix = 2
    while True:
        candidate = f"{base_name} ({suffix})"
        if candidate not in existing:
            return candidate
        suffix += 1


def _resolve_progression(value: Any) -> ProgressionStrategy:
    if isinstance(value, ProgressionStrategy):
        return value
    if isinstance(value, str):
        try:
            return ProgressionStrategy(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=500, detail=f"Unknown progression_strategy {value!r}."
            ) from exc
    return ProgressionStrategy.none


async def copy_template_to_program(
    session: AsyncSession, user: User, template: ProgramTemplate
) -> Program:
    """Atomic: build the full nested program in one transaction.

    `template.data` has shape:
        {
          "slug_map": { "bench": "barbell-bench-press---medium-grip", ... },
          "days": [
              {"name": "Push A", "exercises": [
                  {"slug_key": "bench", "sets": 4, "reps_low": 6, "reps_high": 8,
                   "rpe_low": 7, "rpe_high": 8, "rest_seconds": 180,
                   "progression": "double_progression", "notes": null},
                  ...
              ]},
              ...
          ]
        }
    """
    data = template.data
    slug_map: dict[str, str] = data.get("slug_map", {})
    days_data = data.get("days", [])

    # Resolve every slug up front; fail before any insert if anything is missing.
    needed_slugs = list({slug for slug in slug_map.values()})
    if needed_slugs:
        rows = (
            (await session.execute(select(Exercise).where(Exercise.slug.in_(needed_slugs))))
            .scalars()
            .all()
        )
        by_slug = {row.slug: row for row in rows}
        missing = [slug for slug in needed_slugs if slug not in by_slug]
        if missing:
            raise HTTPException(
                status_code=409,
                detail=f"Template references missing exercise slugs: {sorted(missing)}",
            )
    else:
        by_slug = {}

    name = await _disambiguate_name(session, user.id, template.name)

    program = Program(
        owner_id=user.id,
        name=name,
        description=template.description,
        goal=template.goal,
        weeks=template.weeks,
        days_per_week=template.days_per_week,
        source=ProgramSource.template,
        template_id=template.id,
    )
    session.add(program)
    await session.flush()

    for day_index, day_data in enumerate(days_data):
        day = ProgramDay(
            program_id=program.id,
            day_index=day_index,
            name=day_data["name"],
        )
        session.add(day)
        await session.flush()

        for position, ex_data in enumerate(day_data.get("exercises", [])):
            slug_key = ex_data["slug_key"]
            real_slug = slug_map[slug_key]
            exercise = by_slug[real_slug]
            pde = ProgramDayExercise(
                program_day_id=day.id,
                exercise_id=exercise.id,
                position=position,
                target_sets=ex_data["sets"],
                target_reps_low=ex_data.get("reps_low"),
                target_reps_high=ex_data.get("reps_high"),
                target_rpe_low=ex_data.get("rpe_low"),
                target_rpe_high=ex_data.get("rpe_high"),
                target_rir_low=ex_data.get("rir_low"),
                target_rir_high=ex_data.get("rir_high"),
                rest_seconds=ex_data.get("rest_seconds"),
                progression_strategy=_resolve_progression(ex_data.get("progression")),
                notes=ex_data.get("notes"),
            )
            session.add(pde)

    await session.flush()
    return program


async def get_program_full(session: AsyncSession, user: User, program_id: UUID) -> Program:
    stmt = (
        select(Program)
        .where(
            Program.id == program_id,
            Program.owner_id == user.id,
            Program.deleted_at.is_(None),
        )
        .options(selectinload(Program.days).selectinload(ProgramDay.exercises))
    )
    record = (await session.execute(stmt)).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Program not found.")
    return record


async def list_my_programs(session: AsyncSession, user: User) -> list[Program]:
    stmt = (
        select(Program)
        .where(Program.owner_id == user.id, Program.deleted_at.is_(None))
        .order_by(Program.is_active.desc(), Program.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def create_empty_program(
    session: AsyncSession, user: User, payload: ProgramCreate
) -> Program:
    program = Program(
        owner_id=user.id,
        name=payload.name,
        description=payload.description,
        goal=payload.goal,
        weeks=payload.weeks,
        days_per_week=payload.days_per_week,
        source=ProgramSource.manual,
    )
    session.add(program)
    await session.flush()
    return program


async def _owned_program(session: AsyncSession, user: User, program_id: UUID) -> Program:
    record = (
        await session.execute(
            select(Program).where(
                Program.id == program_id,
                Program.owner_id == user.id,
                Program.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Program not found.")
    return record


async def update_program(
    session: AsyncSession, user: User, program_id: UUID, payload: ProgramUpdate
) -> Program:
    record = await _owned_program(session, user, program_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    await session.flush()
    return record


async def delete_program(session: AsyncSession, user: User, program_id: UUID) -> None:
    record = await _owned_program(session, user, program_id)
    record.deleted_at = _now()
    record.is_active = False
    await session.flush()


async def add_day(
    session: AsyncSession, user: User, program_id: UUID, payload: ProgramDayCreate
) -> ProgramDay:
    program = await _owned_program(session, user, program_id)
    next_index = (
        await session.execute(
            select(func.coalesce(func.max(ProgramDay.day_index) + 1, 0)).where(
                ProgramDay.program_id == program.id
            )
        )
    ).scalar_one()
    day = ProgramDay(
        program_id=program.id,
        day_index=int(next_index),
        name=payload.name,
    )
    session.add(day)
    await session.flush()
    return day


async def _owned_day(session: AsyncSession, user: User, day_id: UUID) -> ProgramDay:
    record = (
        await session.execute(
            select(ProgramDay)
            .join(Program, Program.id == ProgramDay.program_id)
            .where(
                ProgramDay.id == day_id,
                Program.owner_id == user.id,
                Program.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Program day not found.")
    return record


async def delete_day(session: AsyncSession, user: User, day_id: UUID) -> None:
    record = await _owned_day(session, user, day_id)
    program_id = record.program_id
    deleted_index = record.day_index
    await session.delete(record)
    await session.flush()
    await session.execute(
        update(ProgramDay)
        .where(
            ProgramDay.program_id == program_id,
            ProgramDay.day_index > deleted_index,
        )
        .values(day_index=ProgramDay.day_index - 1)
    )
    await session.flush()


async def add_exercise_to_day(
    session: AsyncSession,
    user: User,
    day_id: UUID,
    payload: ProgramDayExerciseCreate,
) -> ProgramDayExercise:
    day = await _owned_day(session, user, day_id)
    exercise = (
        await session.execute(select(Exercise).where(Exercise.id == payload.exercise_id))
    ).scalar_one_or_none()
    if exercise is None or (exercise.owner_id is not None and exercise.owner_id != user.id):
        raise HTTPException(status_code=404, detail="Exercise not found.")

    next_position = (
        await session.execute(
            select(func.coalesce(func.max(ProgramDayExercise.position) + 1, 0)).where(
                ProgramDayExercise.program_day_id == day.id
            )
        )
    ).scalar_one()
    record = ProgramDayExercise(
        program_day_id=day.id,
        exercise_id=exercise.id,
        position=int(next_position),
        target_sets=payload.target_sets,
        target_reps_low=payload.target_reps_low,
        target_reps_high=payload.target_reps_high,
        target_rpe_low=payload.target_rpe_low,
        target_rpe_high=payload.target_rpe_high,
        target_rir_low=payload.target_rir_low,
        target_rir_high=payload.target_rir_high,
        rest_seconds=payload.rest_seconds,
        progression_strategy=payload.progression_strategy,
        notes=payload.notes,
    )
    session.add(record)
    await session.flush()
    return record


async def _owned_program_exercise(
    session: AsyncSession, user: User, pde_id: UUID
) -> ProgramDayExercise:
    record = (
        await session.execute(
            select(ProgramDayExercise)
            .join(ProgramDay, ProgramDay.id == ProgramDayExercise.program_day_id)
            .join(Program, Program.id == ProgramDay.program_id)
            .where(
                ProgramDayExercise.id == pde_id,
                Program.owner_id == user.id,
                Program.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Program exercise not found.")
    return record


async def update_program_exercise(
    session: AsyncSession,
    user: User,
    pde_id: UUID,
    payload: ProgramDayExerciseUpdate,
) -> ProgramDayExercise:
    record = await _owned_program_exercise(session, user, pde_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    await session.flush()
    return record


async def delete_program_exercise(session: AsyncSession, user: User, pde_id: UUID) -> None:
    record = await _owned_program_exercise(session, user, pde_id)
    day_id = record.program_day_id
    deleted_pos = record.position
    await session.delete(record)
    await session.flush()
    await session.execute(
        update(ProgramDayExercise)
        .where(
            ProgramDayExercise.program_day_id == day_id,
            ProgramDayExercise.position > deleted_pos,
        )
        .values(position=ProgramDayExercise.position - 1)
    )
    await session.flush()


# ---------------------------------------------------------------------------
# Activate / deactivate
# ---------------------------------------------------------------------------


def _first_occurrence(start: date, target_weekday: int) -> date:
    """Return the first date >= start whose .weekday() equals target_weekday (0=Mon)."""
    delta = (target_weekday - start.weekday()) % 7
    return start + timedelta(days=delta)


async def _deactivate_user_active_programs(
    session: AsyncSession, user_id: UUID, *, skip_existing: bool
) -> int:
    """Deactivate any current active program and optionally skip future schedules."""
    active_rows = (
        (
            await session.execute(
                select(Program).where(
                    Program.owner_id == user_id,
                    Program.is_active.is_(True),
                    Program.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    skipped = 0
    today = date.today()
    for program in active_rows:
        program.is_active = False
        if skip_existing:
            result = await session.execute(
                update(ScheduledWorkout)
                .where(
                    ScheduledWorkout.program_id == program.id,
                    ScheduledWorkout.scheduled_for >= today,
                    ScheduledWorkout.status == ScheduledWorkoutStatus.planned,
                )
                .values(status=ScheduledWorkoutStatus.skipped)
            )
            skipped += int(result.rowcount or 0)  # type: ignore[attr-defined]
    if active_rows:
        await session.flush()
    return skipped


async def activate_program(
    session: AsyncSession,
    user: User,
    program_id: UUID,
    *,
    start_date: date,
    weekday_offset: int,
    skip_existing: bool,
) -> tuple[Program, int, int]:
    """Generate scheduled_workouts and mark program active.

    Returns (program, scheduled_count, skipped_count). Atomic in one transaction
    via the caller's session.commit().
    """
    program = await _owned_program(session, user, program_id)
    if program.days_per_week <= 0 or program.weeks <= 0:
        raise HTTPException(
            status_code=409,
            detail="Program must have weeks and days_per_week set before activating.",
        )

    # Fetch days in order.
    days = (
        (
            await session.execute(
                select(ProgramDay)
                .where(ProgramDay.program_id == program.id)
                .order_by(ProgramDay.day_index)
            )
        )
        .scalars()
        .all()
    )
    if len(days) != program.days_per_week:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Program has {len(days)} day(s) but days_per_week={program.days_per_week}. "
                "Add or remove days before activating."
            ),
        )

    skipped = await _deactivate_user_active_programs(session, user.id, skip_existing=skip_existing)

    program.is_active = True
    program.activated_at = _now()
    await session.flush()

    first_date = _first_occurrence(start_date, weekday_offset)
    meso_length = program.mesocycle_length_weeks
    auto_deload = program.auto_deload
    scheduled_count = 0
    for week in range(program.weeks):
        abs_week = week + 1
        position = compute_mesocycle_position(meso_length, program.weeks, abs_week)
        is_deload = auto_deload and position.is_deload
        for day_index, day in enumerate(days):
            d = first_date + timedelta(weeks=week, days=day_index)
            session.add(
                ScheduledWorkout(
                    user_id=user.id,
                    program_id=program.id,
                    program_day_id=day.id,
                    scheduled_for=d,
                    status=ScheduledWorkoutStatus.planned,
                    mesocycle_week=position.week_in_meso,
                    is_deload=is_deload,
                )
            )
            scheduled_count += 1
    await session.flush()
    return program, scheduled_count, skipped


async def mesocycle_position(session: AsyncSession, user: User, program_id: UUID) -> dict[str, Any]:
    """Return the user's current mesocycle position for a program.

    Picks the next planned scheduled workout (>= today) as the "current week"
    anchor. If the program has no planned future sessions, returns the last
    completed week's position.
    """
    program = await _owned_program(session, user, program_id)
    today = date.today()
    anchor = (
        await session.execute(
            select(ScheduledWorkout)
            .where(
                ScheduledWorkout.program_id == program.id,
                ScheduledWorkout.user_id == user.id,
                ScheduledWorkout.scheduled_for >= today,
                ScheduledWorkout.status.in_(
                    (
                        ScheduledWorkoutStatus.planned,
                        ScheduledWorkoutStatus.in_progress,
                    )
                ),
            )
            .order_by(ScheduledWorkout.scheduled_for)
            .limit(1)
        )
    ).scalar_one_or_none()
    if anchor is None:
        anchor = (
            await session.execute(
                select(ScheduledWorkout)
                .where(
                    ScheduledWorkout.program_id == program.id,
                    ScheduledWorkout.user_id == user.id,
                )
                .order_by(ScheduledWorkout.scheduled_for.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
    if anchor is None:
        return {
            "mesocycle_length_weeks": program.mesocycle_length_weeks,
            "auto_deload": program.auto_deload,
            "current_week": None,
            "week_in_meso": None,
            "is_deload": False,
            "next_week_is_deload": False,
        }

    # Compute absolute week from scheduled_for relative to the program's first
    # scheduled session.
    first = (
        await session.execute(
            select(ScheduledWorkout.scheduled_for)
            .where(
                ScheduledWorkout.program_id == program.id,
                ScheduledWorkout.user_id == user.id,
            )
            .order_by(ScheduledWorkout.scheduled_for)
            .limit(1)
        )
    ).scalar_one()
    abs_week = ((anchor.scheduled_for - first).days // 7) + 1
    from app.services.progression.mesocycle import compute_mesocycle_position as _cmp

    pos = _cmp(program.mesocycle_length_weeks, program.weeks, abs_week)
    next_is_deload = False
    if abs_week < program.weeks:
        next_pos = _cmp(program.mesocycle_length_weeks, program.weeks, abs_week + 1)
        next_is_deload = next_pos.is_deload
    return {
        "mesocycle_length_weeks": program.mesocycle_length_weeks,
        "auto_deload": program.auto_deload,
        "current_week": abs_week,
        "week_in_meso": pos.week_in_meso,
        "is_deload": pos.is_deload,
        "next_week_is_deload": next_is_deload,
    }


async def trigger_deload(
    session: AsyncSession, user: User, program_id: UUID
) -> tuple[int, list[date]]:
    """Mark every planned scheduled workout in the current week as a deload.

    "Current week" = the Monday-Sunday block containing today's date in the
    user's local calendar (server-tz approximation). Returns (count, dates).
    Future weeks are left as the activation set them. Subsequent sessions
    receive an updated recommendation when the user finishes the next deload
    session via the orchestrator's deload short-circuit.
    """
    program = await _owned_program(session, user, program_id)
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    rows = (
        (
            await session.execute(
                select(ScheduledWorkout).where(
                    ScheduledWorkout.program_id == program.id,
                    ScheduledWorkout.user_id == user.id,
                    ScheduledWorkout.scheduled_for >= monday,
                    ScheduledWorkout.scheduled_for <= sunday,
                    ScheduledWorkout.status == ScheduledWorkoutStatus.planned,
                )
            )
        )
        .scalars()
        .all()
    )
    affected_dates: list[date] = []
    for sw in rows:
        sw.is_deload = True
        affected_dates.append(sw.scheduled_for)
    await session.flush()
    return len(rows), sorted(affected_dates)


async def deactivate_program(
    session: AsyncSession, user: User, program_id: UUID, *, skip_existing: bool
) -> int:
    program = await _owned_program(session, user, program_id)
    if not program.is_active:
        return 0
    program.is_active = False
    skipped = 0
    if skip_existing:
        today = date.today()
        result = await session.execute(
            update(ScheduledWorkout)
            .where(
                ScheduledWorkout.program_id == program.id,
                ScheduledWorkout.scheduled_for >= today,
                ScheduledWorkout.status == ScheduledWorkoutStatus.planned,
            )
            .values(status=ScheduledWorkoutStatus.skipped)
        )
        skipped = int(result.rowcount or 0)  # type: ignore[attr-defined]
    await session.flush()
    return skipped


__all__ = [
    "ProgramGoal",
    "activate_program",
    "add_day",
    "add_exercise_to_day",
    "copy_template_to_program",
    "create_empty_program",
    "deactivate_program",
    "delete_day",
    "delete_program",
    "delete_program_exercise",
    "get_program_full",
    "get_template_by_slug",
    "list_my_programs",
    "list_templates",
    "mesocycle_position",
    "trigger_deload",
    "update_program",
    "update_program_exercise",
]
