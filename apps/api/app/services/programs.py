from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    IntensityMode,
    PeriodizationMode,
    ProgramGoal,
    ProgramSource,
    ProgressionStrategy,
    RepMode,
    ScheduledWorkoutStatus,
)
from app.models.exercise import Exercise
from app.models.exercise_progression import ExerciseProgression
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
from app.services.pagination import decode_cursor, encode_cursor
from app.services.progression.mesocycle import (
    DELOAD_INTENSITY_FACTOR,
    compute_mesocycle_position,
)

DEFAULT_LIMIT = 50
MAX_LIMIT = 100

# Rolling-calendar tunables for continuous programs. The auto-extend keeps at
# least CONTINUOUS_MIN_FUTURE_WEEKS of future sessions on the calendar; each
# extension appends CONTINUOUS_EXTEND_WEEKS more weeks of the day rotation.
CONTINUOUS_MIN_FUTURE_WEEKS = 2
CONTINUOUS_EXTEND_WEEKS = 4


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


def _derive_intensity_mode(days_data: list[dict[str, Any]]) -> IntensityMode:
    """Pick the program's global intensity scale from the template content.

    The template DSL carries per-exercise rpe_*/rir_* values but no explicit
    program-level scale. Prefer RPE if any exercise specifies an rpe value, else
    RIR if any specifies an rir value, else Off (e.g. percentage/AMRAP plans).
    """
    has_rpe = False
    has_rir = False
    for day_data in days_data:
        for ex_data in day_data.get("exercises", []):
            if ex_data.get("rpe_low") is not None or ex_data.get("rpe_high") is not None:
                has_rpe = True
            if ex_data.get("rir_low") is not None or ex_data.get("rir_high") is not None:
                has_rir = True
    if has_rpe:
        return IntensityMode.rpe
    if has_rir:
        return IntensityMode.rir
    return IntensityMode.off


def _derive_rep_mode(ex_data: dict[str, Any]) -> RepMode:
    """A span (reps_high present and != reps_low) is a range; otherwise a single
    rep goal (target)."""
    reps_low = ex_data.get("reps_low")
    reps_high = ex_data.get("reps_high")
    if reps_high is not None and reps_high != reps_low:
        return RepMode.range
    return RepMode.target


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
        intensity_mode=_derive_intensity_mode(days_data),
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
                rep_mode=_derive_rep_mode(ex_data),
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


async def list_my_programs(
    session: AsyncSession,
    user: User,
    *,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> tuple[list[Program], str | None]:
    """Programs ordered (is_active desc, created_at desc, id desc) with keyset
    pagination over the same 3-key ordering."""
    limit = max(1, min(limit, MAX_LIMIT))
    stmt = (
        select(Program)
        .where(Program.owner_id == user.id, Program.deleted_at.is_(None))
        .order_by(Program.is_active.desc(), Program.created_at.desc(), Program.id.desc())
        .limit(limit + 1)
    )

    decoded = decode_cursor(cursor)
    if decoded is not None:
        try:
            cursor_active = bool(decoded["a"])
            cursor_created = datetime.fromisoformat(decoded["c"])
            cursor_id = UUID(decoded["i"])
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid cursor.") from exc
        created_id_after = or_(
            Program.created_at < cursor_created,
            and_(Program.created_at == cursor_created, Program.id < cursor_id),
        )
        if cursor_active:
            stmt = stmt.where(
                or_(
                    Program.is_active.is_(False),
                    and_(Program.is_active.is_(True), created_id_after),
                )
            )
        else:
            stmt = stmt.where(Program.is_active.is_(False), created_id_after)

    rows = list((await session.execute(stmt)).scalars().all())
    next_cursor: str | None = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = encode_cursor(
            {"a": last.is_active, "c": last.created_at.isoformat(), "i": str(last.id)}
        )
    return rows, next_cursor


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
        periodization_mode=payload.periodization_mode,
        auto_deload_on_stall=payload.auto_deload_on_stall,
        intensity_mode=payload.intensity_mode,
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
    changes = payload.model_dump(exclude_unset=True)
    prior_mode = record.periodization_mode
    for field, value in changes.items():
        setattr(record, field, value)
    await session.flush()

    # If the periodization mode actually flipped on an ACTIVE program, re-derive
    # its FUTURE scheduled workouts. Past/completed rows are never touched.
    new_mode = record.periodization_mode
    if record.is_active and "periodization_mode" in changes and new_mode != prior_mode:
        await _rederive_future_schedule(session, user, record)
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
        rep_mode=payload.rep_mode,
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
    updates = payload.model_dump(exclude_unset=True)
    # Validate the merged result: a partial patch must not leave reps_high set
    # without reps_low, or an inverted range.
    new_low = updates.get("target_reps_low", record.target_reps_low)
    new_high = updates.get("target_reps_high", record.target_reps_high)
    if new_high is not None and (new_low is None or new_high < new_low):
        raise HTTPException(
            status_code=422,
            detail="target_reps_high requires target_reps_low <= target_reps_high.",
        )
    for field, value in updates.items():
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
    scheduled_count = _generate_schedule_rows(
        session,
        user=user,
        program=program,
        days=list(days),
        first_date=first_date,
        start_week=0,
        num_weeks=program.weeks,
    )
    await session.flush()
    return program, scheduled_count, skipped


def _generate_schedule_rows(
    session: AsyncSession,
    *,
    user: User,
    program: Program,
    days: list[ProgramDay],
    first_date: date,
    start_week: int,
    num_weeks: int,
) -> int:
    """Add `num_weeks` of scheduled workouts for the day rotation, starting at
    absolute week index `start_week` (0-based) anchored at `first_date`.

    Block mode applies mesocycle framing + deloads via the existing computation.
    Continuous mode emits a rolling calendar with `is_deload=False` always and
    `mesocycle_week=None` (no block framing). Returns the number of rows added.
    """
    is_continuous = program.periodization_mode == PeriodizationMode.continuous
    meso_length = program.mesocycle_length_weeks
    auto_deload = program.auto_deload
    count = 0
    for offset in range(num_weeks):
        week = start_week + offset
        if is_continuous:
            mesocycle_week: int | None = None
            is_deload = False
        else:
            abs_week = week + 1
            position = compute_mesocycle_position(meso_length, program.weeks, abs_week)
            mesocycle_week = position.week_in_meso
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
                    mesocycle_week=mesocycle_week,
                    is_deload=is_deload,
                )
            )
            count += 1
    return count


# ---------------------------------------------------------------------------
# Rolling calendar (continuous programs)
# ---------------------------------------------------------------------------


async def _program_days_ordered(session: AsyncSession, program_id: UUID) -> list[ProgramDay]:
    return list(
        (
            await session.execute(
                select(ProgramDay)
                .where(ProgramDay.program_id == program_id)
                .order_by(ProgramDay.day_index)
            )
        )
        .scalars()
        .all()
    )


async def _schedule_anchor(
    session: AsyncSession, user_id: UUID, program_id: UUID
) -> tuple[date, int] | None:
    """Return (first_scheduled_date, last_week_offset) for the program's
    existing planned/in-progress/completed rows, or None if it has none.

    `last_week_offset` is the 0-based whole-week offset of the furthest-out
    scheduled row from the first date, so the next chunk can continue both the
    absolute week counter and the day rotation.
    """
    first = (
        await session.execute(
            select(func.min(ScheduledWorkout.scheduled_for)).where(
                ScheduledWorkout.program_id == program_id,
                ScheduledWorkout.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    last = (
        await session.execute(
            select(func.max(ScheduledWorkout.scheduled_for)).where(
                ScheduledWorkout.program_id == program_id,
                ScheduledWorkout.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if first is None or last is None:
        return None
    last_week_offset = (last - first).days // 7
    return first, last_week_offset


async def extend_continuous_schedule(session: AsyncSession, user: User, program: Program) -> int:
    """Top up a continuous program's rolling calendar.

    If fewer than CONTINUOUS_MIN_FUTURE_WEEKS of future planned sessions remain,
    append CONTINUOUS_EXTEND_WEEKS more weeks of the day rotation (continuing the
    absolute week counter, no deloads). Idempotent: a no-op when enough future
    sessions already exist. Returns the number of rows added.
    """
    if not program.is_active or program.periodization_mode != PeriodizationMode.continuous:
        return 0

    today = date.today()
    horizon = today + timedelta(weeks=CONTINUOUS_MIN_FUTURE_WEEKS)
    future_count = (
        await session.execute(
            select(func.count())
            .select_from(ScheduledWorkout)
            .where(
                ScheduledWorkout.program_id == program.id,
                ScheduledWorkout.user_id == user.id,
                ScheduledWorkout.status == ScheduledWorkoutStatus.planned,
                ScheduledWorkout.scheduled_for >= today,
                ScheduledWorkout.scheduled_for <= horizon,
            )
        )
    ).scalar_one()
    days = await _program_days_ordered(session, program.id)
    needed = CONTINUOUS_MIN_FUTURE_WEEKS * max(len(days), 1)
    if int(future_count) >= needed:
        return 0

    anchor = await _schedule_anchor(session, user.id, program.id)
    if anchor is None or not days:
        return 0
    first_date, last_week_offset = anchor
    added = _generate_schedule_rows(
        session,
        user=user,
        program=program,
        days=days,
        first_date=first_date,
        start_week=last_week_offset + 1,
        num_weeks=CONTINUOUS_EXTEND_WEEKS,
    )
    await session.flush()
    return added


async def _rederive_future_schedule(session: AsyncSession, user: User, program: Program) -> None:
    """Re-derive FUTURE planned scheduled workouts after a mode switch on an
    active program. Past/completed/in-progress rows are left untouched.

    block -> continuous: clear deload + mesocycle framing on future rows and
        ensure a rolling horizon exists.
    continuous -> block: recompute deload + mesocycle_week for future rows using
        the block generator's per-week layout, keyed off each row's week offset
        from the program's first scheduled session.
    """
    today = date.today()
    future_rows = list(
        (
            await session.execute(
                select(ScheduledWorkout)
                .where(
                    ScheduledWorkout.program_id == program.id,
                    ScheduledWorkout.user_id == user.id,
                    ScheduledWorkout.status == ScheduledWorkoutStatus.planned,
                    ScheduledWorkout.scheduled_for >= today,
                )
                .order_by(ScheduledWorkout.scheduled_for)
            )
        )
        .scalars()
        .all()
    )

    if program.periodization_mode == PeriodizationMode.continuous:
        for row in future_rows:
            row.is_deload = False
            row.mesocycle_week = None
        await session.flush()
        await extend_continuous_schedule(session, user, program)
        return

    # continuous -> block: recompute framing per row using its week offset.
    anchor = await _schedule_anchor(session, user.id, program.id)
    if anchor is None:
        await session.flush()
        return
    first_date, _ = anchor
    meso_length = program.mesocycle_length_weeks
    auto_deload = program.auto_deload
    for row in future_rows:
        abs_week = ((row.scheduled_for - first_date).days // 7) + 1
        if abs_week < 1 or abs_week > program.weeks:
            # Rolling rows can sit beyond the finite block; clamp framing off.
            row.mesocycle_week = None
            row.is_deload = False
            continue
        position = compute_mesocycle_position(meso_length, program.weeks, abs_week)
        row.mesocycle_week = position.week_in_meso
        row.is_deload = auto_deload and position.is_deload
    await session.flush()


# ---------------------------------------------------------------------------
# Per-lift reactive deload (continuous mode)
# ---------------------------------------------------------------------------


async def apply_exercise_deload(
    session: AsyncSession, user: User, program_id: UUID, exercise_id: UUID
) -> tuple[Decimal | None, Decimal | None]:
    """Reduce a single exercise's working weight by the deload intensity factor
    and reset its progression counters so it ramps from scratch.

    Scoped to ONE exercise; never touches the rest of the program or the
    scheduled calendar. Returns (prior_weight_kg, new_weight_kg).
    """
    program = await _owned_program(session, user, program_id)
    prog = (
        await session.execute(
            select(ExerciseProgression).where(
                ExerciseProgression.user_id == user.id,
                ExerciseProgression.exercise_id == exercise_id,
            )
        )
    ).scalar_one_or_none()
    if prog is None:
        # No progression state yet -> nothing to deload, but the request is
        # still scoped/valid. Create a zeroed row so counters are reset.
        prog = ExerciseProgression(user_id=user.id, exercise_id=exercise_id)
        session.add(prog)
        await session.flush()

    prior = prog.current_top_set_weight_kg
    new_weight: Decimal | None = None
    if prior is not None:
        raw = prior * DELOAD_INTENSITY_FACTOR
        new_weight = ((raw / Decimal("0.5")).quantize(Decimal("1")) * Decimal("0.5")).quantize(
            Decimal("0.01")
        )
        prog.current_top_set_weight_kg = new_weight

    prog.consecutive_failures = 0
    prog.consecutive_successes = 0
    prog.consecutive_above_range = 0
    prog.last_updated_at = _now()

    # Dismiss any active per-lift stagnation suggestion for this exercise so it
    # doesn't keep nagging once the user has acted on it.
    await _dismiss_exercise_deload_suggestion(session, user, program, exercise_id)
    await session.flush()
    return prior, new_weight


def _stagnation_subject(exercise_slug: str) -> str:
    return exercise_slug


async def _dismiss_exercise_deload_suggestion(
    session: AsyncSession, user: User, program: Program, exercise_id: UUID
) -> None:
    """Mark the active reactive-deload stagnation insight for this exercise as
    dismissed, if one exists. Looks the insight up by the exercise's slug, which
    is the stagnation `subject`.
    """
    from app.models.analytics_insight import AnalyticsInsight
    from app.models.enums import AnalyticsInsightKind

    slug = (
        await session.execute(select(Exercise.slug).where(Exercise.id == exercise_id))
    ).scalar_one_or_none()
    if slug is None:
        return
    rows = (
        (
            await session.execute(
                select(AnalyticsInsight).where(
                    AnalyticsInsight.user_id == user.id,
                    AnalyticsInsight.kind == AnalyticsInsightKind.stagnation,
                    AnalyticsInsight.subject == _stagnation_subject(slug),
                    AnalyticsInsight.dismissed_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        row.dismissed_at = _now()


async def mesocycle_position(session: AsyncSession, user: User, program_id: UUID) -> dict[str, Any]:
    """Return the user's current mesocycle position for a program.

    Picks the next planned scheduled workout (>= today) as the "current week"
    anchor. If the program has no planned future sessions, returns the last
    completed week's position.
    """
    program = await _owned_program(session, user, program_id)

    # Continuous programs have no block framing: no week-of-N, no scheduled
    # deload. Signal continuous explicitly and null/false the block fields.
    if program.periodization_mode == PeriodizationMode.continuous:
        return {
            "periodization_mode": PeriodizationMode.continuous,
            "is_continuous": True,
            "mesocycle_length_weeks": program.mesocycle_length_weeks,
            "auto_deload": program.auto_deload,
            "current_week": None,
            "week_in_meso": None,
            "is_deload": False,
            "next_week_is_deload": False,
        }

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
            "periodization_mode": program.periodization_mode,
            "is_continuous": False,
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
        "periodization_mode": program.periodization_mode,
        "is_continuous": False,
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
    "apply_exercise_deload",
    "copy_template_to_program",
    "create_empty_program",
    "deactivate_program",
    "delete_day",
    "delete_program",
    "delete_program_exercise",
    "extend_continuous_schedule",
    "get_program_full",
    "get_template_by_slug",
    "list_my_programs",
    "list_templates",
    "mesocycle_position",
    "trigger_deload",
    "update_program",
    "update_program_exercise",
]
