from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    BlockKind,
    ScheduledWorkoutStatus,
    SegmentKind,
    SetType,
    TrackingType,
)
from app.models.exercise import Exercise
from app.models.exercise_progression import ExerciseProgression
from app.models.user import User
from app.models.workout import SetSegment, WorkoutExercise, WorkoutSession, WorkoutSet
from app.observability.spans import traced_span
from app.schemas.workout import (
    SetCreate,
    SetUpdate,
    WorkoutExerciseCreate,
    WorkoutExerciseSwap,
    WorkoutExerciseUpdate,
    WorkoutSessionCreate,
    WorkoutSessionUpdate,
    validate_set_payload,
)
from app.services.pagination import (
    decode_cursor,
    encode_cursor,
)

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
RESTORE_WINDOW_DAYS = 30


def _now() -> datetime:
    return datetime.now(tz=UTC)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


async def create_session(
    session: AsyncSession, user: User, payload: WorkoutSessionCreate
) -> WorkoutSession:
    record = WorkoutSession(
        user_id=user.id,
        name=payload.name,
        scheduled_workout_id=payload.scheduled_workout_id,
    )
    if payload.started_at is not None:
        record.started_at = payload.started_at
    session.add(record)
    await session.flush()
    return record


async def repeat_session(
    session: AsyncSession, user: User, source_session_id: UUID
) -> WorkoutSession:
    """Clone a workout session for TODAY, prefilling last performance as targets.

    Copies every exercise (preserving order + notes) and re-creates each set with
    the source session's weight/reps/duration/distance as prefilled *targets*, but
    marks the new sets as not-yet-completed (`is_pr` reset, `rpe`/`rir` cleared, and
    `set_type` carried over). The new session is unfinished (`ended_at is None`),
    unlinked from any scheduled workout, and `started_at` defaults to now (today).
    """
    source = await get_session_full(session, user, source_session_id)

    new_name = source.name
    clone = WorkoutSession(
        user_id=user.id,
        name=new_name,
        # Intentionally NOT linked to a scheduled workout: a repeat is free-style.
        scheduled_workout_id=None,
        # started_at defaults to now() (today) via the server default.
        notes=source.notes,
    )
    session.add(clone)
    await session.flush()

    for src_ex in source.workout_exercises:
        new_ex = WorkoutExercise(
            workout_session_id=clone.id,
            exercise_id=src_ex.exercise_id,
            position=src_ex.position,
            notes=src_ex.notes,
        )
        session.add(new_ex)
        await session.flush()

        for src_set in src_ex.sets:
            session.add(
                WorkoutSet(
                    workout_exercise_id=new_ex.id,
                    set_index=src_set.set_index,
                    set_type=src_set.set_type,
                    # Prefill last performance as the target for the new (blank) set.
                    weight_kg=src_set.weight_kg,
                    reps=src_set.reps,
                    duration_seconds=src_set.duration_seconds,
                    distance_meters=src_set.distance_meters,
                    # Not-yet-completed: no effort logged, no PR carried over.
                    rpe=None,
                    rir=None,
                    is_pr=False,
                    notes=None,
                )
            )

    await session.flush()
    return clone


async def get_session_full(session: AsyncSession, user: User, session_id: UUID) -> WorkoutSession:
    stmt = (
        select(WorkoutSession)
        .where(
            WorkoutSession.id == session_id,
            WorkoutSession.user_id == user.id,
            WorkoutSession.deleted_at.is_(None),
        )
        .options(
            selectinload(WorkoutSession.workout_exercises)
            .selectinload(WorkoutExercise.sets)
            .selectinload(WorkoutSet.segments)
        )
    )
    record = (await session.execute(stmt)).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Workout session not found.")
    return record


async def list_sessions(
    session: AsyncSession,
    user: User,
    *,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> tuple[list[WorkoutSession], str | None]:
    limit = max(1, min(limit, MAX_LIMIT))

    stmt = (
        select(WorkoutSession)
        .where(
            WorkoutSession.user_id == user.id,
            WorkoutSession.deleted_at.is_(None),
        )
        .order_by(desc(WorkoutSession.started_at), desc(WorkoutSession.id))
        .limit(limit + 1)
    )

    if from_dt is not None:
        stmt = stmt.where(WorkoutSession.started_at >= from_dt)
    if to_dt is not None:
        stmt = stmt.where(WorkoutSession.started_at <= to_dt)

    decoded = decode_cursor(cursor)
    if decoded is not None:
        try:
            cursor_started = datetime.fromisoformat(decoded["c"])
            cursor_id = UUID(decoded["i"])
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid cursor.") from exc
        stmt = stmt.where(
            or_(
                WorkoutSession.started_at < cursor_started,
                and_(
                    WorkoutSession.started_at == cursor_started,
                    WorkoutSession.id < cursor_id,
                ),
            )
        )

    rows = (await session.execute(stmt)).scalars().all()
    next_cursor: str | None = None
    if len(rows) > limit:
        rows = list(rows[:limit])
        last = rows[-1]
        next_cursor = encode_cursor({"c": last.started_at.isoformat(), "i": str(last.id)})
    else:
        rows = list(rows)
    return rows, next_cursor


async def _owned_session(
    session: AsyncSession, user: User, session_id: UUID, *, allow_deleted: bool = False
) -> WorkoutSession:
    conditions = [
        WorkoutSession.id == session_id,
        WorkoutSession.user_id == user.id,
    ]
    if not allow_deleted:
        conditions.append(WorkoutSession.deleted_at.is_(None))
    record = (await session.execute(select(WorkoutSession).where(*conditions))).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Workout session not found.")
    return record


async def update_session(
    session: AsyncSession, user: User, session_id: UUID, payload: WorkoutSessionUpdate
) -> WorkoutSession:
    record = await _owned_session(session, user, session_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    await session.flush()
    return record


async def soft_delete_session(session: AsyncSession, user: User, session_id: UUID) -> None:
    record = await _owned_session(session, user, session_id)
    record.deleted_at = _now()
    await session.flush()


async def restore_session(session: AsyncSession, user: User, session_id: UUID) -> WorkoutSession:
    record = await _owned_session(session, user, session_id, allow_deleted=True)
    if record.deleted_at is None:
        return record
    age_days = (_now() - record.deleted_at).days
    if age_days > RESTORE_WINDOW_DAYS:
        raise HTTPException(
            status_code=410,
            detail=f"Session deleted more than {RESTORE_WINDOW_DAYS} days ago.",
        )
    record.deleted_at = None
    await session.flush()
    return record


# ---------------------------------------------------------------------------
# Workout exercises
# ---------------------------------------------------------------------------


async def _next_exercise_position(session: AsyncSession, session_id: UUID) -> int:
    next_pos = (
        await session.execute(
            select(func.coalesce(func.max(WorkoutExercise.position) + 1, 0)).where(
                WorkoutExercise.workout_session_id == session_id
            )
        )
    ).scalar_one()
    return int(next_pos)


async def add_exercise(
    session: AsyncSession,
    user: User,
    session_id: UUID,
    payload: WorkoutExerciseCreate,
) -> WorkoutExercise:
    parent = await _owned_session(session, user, session_id)
    exercise = (
        await session.execute(select(Exercise).where(Exercise.id == payload.exercise_id))
    ).scalar_one_or_none()
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found.")
    if exercise.owner_id is not None and exercise.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Exercise not found.")

    position = (
        payload.position
        if payload.position is not None
        else await _next_exercise_position(session, parent.id)
    )

    record = WorkoutExercise(
        workout_session_id=parent.id,
        exercise_id=exercise.id,
        position=position,
        notes=payload.notes,
        block_kind=payload.block_kind,
        block_label=payload.block_label,
    )
    session.add(record)
    await session.flush()
    return record


async def swap_workout_exercise(
    session: AsyncSession,
    user: User,
    workout_exercise_id: UUID,
    payload: WorkoutExerciseSwap,
) -> WorkoutExercise:
    """Temporary one-session swap: point this row at a substitute exercise and
    record the original as ``substituted_for_exercise_id`` so the original pauses
    (it is neither progressed nor stalled for this slot) while the substitute's
    logged sets credit its own history/progression.
    """
    record = await _owned_workout_exercise(session, user, workout_exercise_id)
    substitute = (
        await session.execute(select(Exercise).where(Exercise.id == payload.substitute_exercise_id))
    ).scalar_one_or_none()
    if substitute is None:
        raise HTTPException(status_code=404, detail="Exercise not found.")
    if substitute.owner_id is not None and substitute.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Exercise not found.")
    if substitute.id == record.exercise_id:
        raise HTTPException(status_code=422, detail="Substitute matches the current exercise.")

    # Preserve the ORIGINAL (the one being replaced) so history reads
    # "<substitute> (in place of <original>)" and progression skips the original.
    record.substituted_for_exercise_id = record.exercise_id
    record.exercise_id = substitute.id
    await session.flush()
    return record


async def _owned_workout_exercise(
    session: AsyncSession, user: User, workout_exercise_id: UUID
) -> WorkoutExercise:
    record = (
        await session.execute(
            select(WorkoutExercise)
            .join(WorkoutSession, WorkoutSession.id == WorkoutExercise.workout_session_id)
            .where(
                WorkoutExercise.id == workout_exercise_id,
                WorkoutSession.user_id == user.id,
                WorkoutSession.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Workout exercise not found.")
    return record


async def get_workout_exercise_full(
    session: AsyncSession, user: User, workout_exercise_id: UUID
) -> WorkoutExercise:
    """Fetch an owned workout exercise with sets + segments eager-loaded for the
    nested response shape."""
    record = (
        await session.execute(
            select(WorkoutExercise)
            .join(WorkoutSession, WorkoutSession.id == WorkoutExercise.workout_session_id)
            .where(
                WorkoutExercise.id == workout_exercise_id,
                WorkoutSession.user_id == user.id,
                WorkoutSession.deleted_at.is_(None),
            )
            .options(selectinload(WorkoutExercise.sets).selectinload(WorkoutSet.segments))
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Workout exercise not found.")
    return record


async def update_workout_exercise(
    session: AsyncSession,
    user: User,
    workout_exercise_id: UUID,
    payload: WorkoutExerciseUpdate,
) -> WorkoutExercise:
    record = await _owned_workout_exercise(session, user, workout_exercise_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    await session.flush()
    return record


async def delete_workout_exercise(
    session: AsyncSession, user: User, workout_exercise_id: UUID
) -> None:
    record = await _owned_workout_exercise(session, user, workout_exercise_id)
    session_id = record.workout_session_id
    deleted_pos = record.position
    await session.delete(record)
    await session.flush()
    # Compact positions so siblings stay contiguous.
    await session.execute(
        update(WorkoutExercise)
        .where(
            WorkoutExercise.workout_session_id == session_id,
            WorkoutExercise.position > deleted_pos,
        )
        .values(position=WorkoutExercise.position - 1)
    )
    await session.flush()


async def reorder_workout_exercise(
    session: AsyncSession,
    user: User,
    workout_exercise_id: UUID,
    new_position: int,
) -> WorkoutExercise:
    record = await _owned_workout_exercise(session, user, workout_exercise_id)
    current_position = record.position
    session_id = record.workout_session_id

    max_position = (
        await session.execute(
            select(func.coalesce(func.max(WorkoutExercise.position), 0)).where(
                WorkoutExercise.workout_session_id == session_id
            )
        )
    ).scalar_one()
    new_position = max(0, min(new_position, int(max_position)))
    if new_position == current_position:
        return record

    if new_position > current_position:
        await session.execute(
            update(WorkoutExercise)
            .where(
                WorkoutExercise.workout_session_id == session_id,
                WorkoutExercise.id != record.id,
                WorkoutExercise.position > current_position,
                WorkoutExercise.position <= new_position,
            )
            .values(position=WorkoutExercise.position - 1)
        )
    else:
        await session.execute(
            update(WorkoutExercise)
            .where(
                WorkoutExercise.workout_session_id == session_id,
                WorkoutExercise.id != record.id,
                WorkoutExercise.position >= new_position,
                WorkoutExercise.position < current_position,
            )
            .values(position=WorkoutExercise.position + 1)
        )

    record.position = new_position
    await session.flush()
    return record


# ---------------------------------------------------------------------------
# Sets
# ---------------------------------------------------------------------------


async def _exercise_tracking_type(
    session: AsyncSession, workout_exercise: WorkoutExercise
) -> TrackingType:
    exercise = (
        await session.execute(
            select(Exercise.tracking_type).where(Exercise.id == workout_exercise.exercise_id)
        )
    ).scalar_one()
    return exercise


async def _next_set_index(session: AsyncSession, workout_exercise_id: UUID) -> int:
    next_index = (
        await session.execute(
            select(func.coalesce(func.max(WorkoutSet.set_index) + 1, 0)).where(
                WorkoutSet.workout_exercise_id == workout_exercise_id
            )
        )
    ).scalar_one()
    return int(next_index)


async def add_set(
    session: AsyncSession,
    user: User,
    workout_exercise_id: UUID,
    payload: SetCreate,
) -> WorkoutSet:
    parent = await _owned_workout_exercise(session, user, workout_exercise_id)
    tracking_type = await _exercise_tracking_type(session, parent)
    try:
        validate_set_payload(payload, tracking_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    set_index = (
        payload.set_index
        if payload.set_index is not None
        else await _next_set_index(session, parent.id)
    )

    record = WorkoutSet(
        workout_exercise_id=parent.id,
        set_index=set_index,
        set_type=payload.set_type,
        weight_kg=payload.weight_kg,
        reps=payload.reps,
        duration_seconds=payload.duration_seconds,
        distance_meters=payload.distance_meters,
        rpe=payload.rpe,
        rir=payload.rir,
        notes=payload.notes,
        rounds=payload.rounds,
    )
    session.add(record)
    await session.flush()

    # Structured-work sub-bouts: rest-pause/cluster/myo ``mini_set`` segments or
    # interval ``work``/``rest`` segments. Index defaults to position in the list.
    for index, seg in enumerate(payload.segments):
        session.add(
            SetSegment(
                set_id=record.id,
                segment_index=seg.segment_index if seg.segment_index is not None else index,
                kind=seg.kind,
                reps=seg.reps,
                weight_kg=seg.weight_kg,
                duration_seconds=seg.duration_seconds,
                distance_meters=seg.distance_meters,
                rest_seconds=seg.rest_seconds,
            )
        )
    if payload.segments:
        await session.flush()
    return record


async def get_set_full(session: AsyncSession, user: User, set_id: UUID) -> WorkoutSet:
    """Fetch an owned set with its segments eager-loaded for the response shape."""
    record = (
        await session.execute(
            select(WorkoutSet)
            .join(WorkoutExercise, WorkoutExercise.id == WorkoutSet.workout_exercise_id)
            .join(WorkoutSession, WorkoutSession.id == WorkoutExercise.workout_session_id)
            .where(
                WorkoutSet.id == set_id,
                WorkoutSession.user_id == user.id,
                WorkoutSession.deleted_at.is_(None),
            )
            .options(selectinload(WorkoutSet.segments))
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Set not found.")
    return record


async def _owned_set(session: AsyncSession, user: User, set_id: UUID) -> WorkoutSet:
    record = (
        await session.execute(
            select(WorkoutSet)
            .join(WorkoutExercise, WorkoutExercise.id == WorkoutSet.workout_exercise_id)
            .join(WorkoutSession, WorkoutSession.id == WorkoutExercise.workout_session_id)
            .where(
                WorkoutSet.id == set_id,
                WorkoutSession.user_id == user.id,
                WorkoutSession.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Set not found.")
    return record


async def update_set(
    session: AsyncSession, user: User, set_id: UUID, payload: SetUpdate
) -> WorkoutSet:
    record = await _owned_set(session, user, set_id)
    parent = (
        await session.execute(
            select(WorkoutExercise).where(WorkoutExercise.id == record.workout_exercise_id)
        )
    ).scalar_one()
    tracking_type = await _exercise_tracking_type(session, parent)
    try:
        validate_set_payload(payload, tracking_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    await session.flush()
    return record


async def delete_set(session: AsyncSession, user: User, set_id: UUID) -> None:
    record = await _owned_set(session, user, set_id)
    workout_exercise_id = record.workout_exercise_id
    deleted_index = record.set_index
    await session.delete(record)
    await session.flush()
    await session.execute(
        update(WorkoutSet)
        .where(
            WorkoutSet.workout_exercise_id == workout_exercise_id,
            WorkoutSet.set_index > deleted_index,
        )
        .values(set_index=WorkoutSet.set_index - 1)
    )
    await session.flush()


# ---------------------------------------------------------------------------
# Finish + PR detection
# ---------------------------------------------------------------------------


def epley_e1rm(weight_kg: Decimal, reps: int) -> Decimal:
    """Epley formula: weight * (1 + reps/30). Returns kg with 2dp precision."""
    if reps <= 0:
        return Decimal("0")
    factor = Decimal("1") + (Decimal(reps) / Decimal("30"))
    return (weight_kg * factor).quantize(Decimal("0.01"))


def effective_reps(s: WorkoutSet) -> int | None:
    """Total reps a set should count for analytics/PRs.

    A rest-pause/cluster/myo set carries its reps in ``mini_set`` segments, so the
    effective rep count is the sum of those segment reps (a 10+3+2 counts as 15).
    Plain straight sets have no segments and use the set's own ``reps`` column.
    """
    seg_total = sum(
        seg.reps for seg in s.segments if seg.kind == SegmentKind.mini_set and seg.reps is not None
    )
    if seg_total:
        return seg_total
    return s.reps


async def _get_or_create_progression(
    session: AsyncSession, user_id: UUID, exercise_id: UUID
) -> ExerciseProgression:
    record = (
        await session.execute(
            select(ExerciseProgression).where(
                ExerciseProgression.user_id == user_id,
                ExerciseProgression.exercise_id == exercise_id,
            )
        )
    ).scalar_one_or_none()
    if record is None:
        record = ExerciseProgression(user_id=user_id, exercise_id=exercise_id)
        session.add(record)
        await session.flush()
    return record


async def _detect_prs_for_exercise(
    session: AsyncSession,
    user_id: UUID,
    workout_exercise: WorkoutExercise,
    tracking_type: TrackingType,
) -> None:
    """Mark `is_pr` on the best set of this exercise within this session
    (if it beats the user's prior best in exercise_progression).
    """
    sets = (
        (
            await session.execute(
                select(WorkoutSet)
                .where(WorkoutSet.workout_exercise_id == workout_exercise.id)
                .options(selectinload(WorkoutSet.segments))
            )
        )
        .scalars()
        .all()
    )
    if not sets:
        return

    # A warm-up single is never a PR: only non-warmup set types are candidates.
    sets = [s for s in sets if s.set_type != SetType.warmup]
    if not sets:
        return

    progression = await _get_or_create_progression(session, user_id, workout_exercise.exercise_id)
    now = _now()

    if tracking_type in (
        TrackingType.weight_reps,
        TrackingType.weighted_bodyweight,
        TrackingType.weight_reps_distance,
    ):
        best_set: WorkoutSet | None = None
        best_e1rm: Decimal | None = None
        for s in sets:
            reps = effective_reps(s)
            if s.weight_kg is None or reps is None:
                continue
            e1rm = epley_e1rm(s.weight_kg, reps)
            if best_e1rm is None or e1rm > best_e1rm:
                best_e1rm = e1rm
                best_set = s
        if (
            best_set is not None
            and best_e1rm is not None
            and (progression.best_e1rm_kg is None or best_e1rm > progression.best_e1rm_kg)
        ):
            best_set.is_pr = True
            progression.best_e1rm_kg = best_e1rm
            progression.last_updated_at = now

    elif tracking_type == TrackingType.bodyweight_reps:
        best_set = None
        best_reps = -1
        for s in sets:
            reps = effective_reps(s)
            if reps is None:
                continue
            if reps > best_reps:
                best_reps = reps
                best_set = s
        if best_set is not None and best_reps >= 0:
            prior = progression.best_reps_bodyweight or -1
            if best_reps > prior:
                best_set.is_pr = True
                progression.best_reps_bodyweight = best_reps
                progression.last_updated_at = now

    elif tracking_type in (TrackingType.distance_time, TrackingType.distance_time_pace):
        best_set = None
        best_pace: Decimal | None = None  # seconds per km, smaller is better
        for s in sets:
            if s.distance_meters is None or s.duration_seconds is None:
                continue
            if s.distance_meters <= 0:
                continue
            pace = (Decimal(s.duration_seconds) * Decimal("1000") / s.distance_meters).quantize(
                Decimal("0.01")
            )
            if best_pace is None or pace < best_pace:
                best_pace = pace
                best_set = s
        if best_set is not None and best_pace is not None:
            prior_pace = progression.best_pace_seconds_per_km
            if prior_pace is None or best_pace < prior_pace:
                best_set.is_pr = True
                progression.best_pace_seconds_per_km = best_pace
                progression.last_updated_at = now

    # time_only and cardio_machine: no canonical PR notion in v1.
    await session.flush()


@dataclass(frozen=True)
class FinishSessionResult:
    record: WorkoutSession
    rec_ids: list[UUID]
    affected_iso_year: int
    affected_iso_week: int
    should_push_to_fitbit: bool


async def finish_session(
    session: AsyncSession, user: User, session_id: UUID
) -> FinishSessionResult:
    """Finish a session. Returns the record + the rec_ids needing rationale
    generation + the ISO year/week the session belongs to + whether to
    enqueue a Fitbit push (auto_push_to_fitbit ON + connection exists).

    The caller must enqueue rationale + rollup + fitbit-push jobs AFTER
    committing, because workers need to read the just-committed rows.
    """
    record = await _owned_session(session, user, session_id)
    with traced_span(
        "db.tx.workouts",
        user_id=user.id,
        attributes={"workout.session_id": str(session_id)},
    ):
        if record.ended_at is None:
            record.ended_at = _now()
        rec_ids = await _finalize_session(session, record)

        anchor = await _session_anchor_date(session, record)
        iso_year, iso_week, _ = anchor.isocalendar()

        if record.scheduled_workout_id is not None:
            from app.services.scheduling import mark_scheduled_completed_for_session

            await mark_scheduled_completed_for_session(session, record.scheduled_workout_id)
            # Completing a program-linked slot consumes it: advance the rotation
            # pointer (non-skip, so completion is stamped). Freestyle sessions
            # (no scheduled link) never reach here and never touch the pointer.
            await _advance_rotation_for_scheduled(
                session, user, record.scheduled_workout_id, as_skip=False
            )
        await session.flush()

    should_push = False
    if user.auto_push_to_fitbit and record.fitbit_pushed_at is None:
        from app.models.fitbit_connection import FitbitConnection

        connected = (
            await session.execute(
                select(FitbitConnection.id).where(FitbitConnection.user_id == user.id)
            )
        ).first()
        should_push = connected is not None

    return FinishSessionResult(
        record=record,
        rec_ids=rec_ids,
        affected_iso_year=iso_year,
        affected_iso_week=iso_week,
        should_push_to_fitbit=should_push,
    )


async def _advance_rotation_for_scheduled(
    session: AsyncSession,
    user: User,
    scheduled_workout_id: UUID,
    *,
    as_skip: bool,
) -> None:
    """Advance the active program rotation pointer for the program that owns the
    given scheduled workout. ``as_skip=True`` advances neutrally (no completion
    stamp). No-op when the scheduled workout isn't tied to a program the user owns.
    """
    from app.models.scheduled_workout import ScheduledWorkout
    from app.services import programs as programs_svc

    scheduled = (
        await session.execute(
            select(ScheduledWorkout).where(ScheduledWorkout.id == scheduled_workout_id)
        )
    ).scalar_one_or_none()
    if scheduled is None or scheduled.program_id is None:
        return
    try:
        await programs_svc.advance_position(session, user, scheduled.program_id, as_skip=as_skip)
    except HTTPException:
        # Program was deleted/unowned in the interim: advancing is best-effort and
        # must never block finishing/skipping the session.
        return


async def skip_session(session: AsyncSession, user: User, session_id: UUID) -> WorkoutSession:
    """Skip a session mid-flight (``05-active-session.md`` section 4).

    Marks the linked scheduled workout ``skipped``, advances the rotation pointer
    neutrally (the slot is consumed, not repeated), and does NOT run progression —
    a skip is neutral and never feeds the stall signal. Any sets already logged
    stay on the session record. The session is ended so it leaves the active state.
    """
    record = await _owned_session(session, user, session_id)
    if record.ended_at is None:
        record.ended_at = _now()

    if record.scheduled_workout_id is not None:
        from app.models.scheduled_workout import ScheduledWorkout

        scheduled = (
            await session.execute(
                select(ScheduledWorkout).where(ScheduledWorkout.id == record.scheduled_workout_id)
            )
        ).scalar_one_or_none()
        if scheduled is not None:
            scheduled.status = ScheduledWorkoutStatus.skipped
            await session.flush()
        await _advance_rotation_for_scheduled(
            session, user, record.scheduled_workout_id, as_skip=True
        )

    await session.flush()
    return record


async def _session_anchor_date(session: AsyncSession, record: WorkoutSession) -> date:
    """Anchor for a session in volume rollups: scheduled_for if linked, else
    the local date of started_at.
    """
    from app.models.scheduled_workout import ScheduledWorkout

    if record.scheduled_workout_id is not None:
        scheduled = (
            await session.execute(
                select(ScheduledWorkout).where(ScheduledWorkout.id == record.scheduled_workout_id)
            )
        ).scalar_one_or_none()
        if scheduled is not None and scheduled.scheduled_for is not None:
            return scheduled.scheduled_for
    return record.started_at.date()


async def _finalize_session(session: AsyncSession, record: WorkoutSession) -> list[UUID]:
    """PR detection + progression orchestration across every workout_exercise.

    Returns the list of recommendation ids that need rationale generation.
    """
    rows = (
        await session.execute(
            select(WorkoutExercise, Exercise.tracking_type)
            .join(Exercise, Exercise.id == WorkoutExercise.exercise_id)
            .where(
                WorkoutExercise.workout_session_id == record.id,
                # PRs are detected on ``working`` blocks only: a warm-up or
                # cooldown single is never a PR.
                WorkoutExercise.block_kind == BlockKind.working,
            )
        )
    ).all()
    for workout_exercise, tracking_type in rows:
        await _detect_prs_for_exercise(session, record.user_id, workout_exercise, tracking_type)

    # Progression: only fires if this workout is linked to a scheduled workout.
    from app.services.progression.orchestrate import apply_progressions_after_finalize

    return await apply_progressions_after_finalize(session, record)
