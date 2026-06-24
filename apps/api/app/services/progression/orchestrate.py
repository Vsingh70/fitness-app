"""After a session is finalized, apply progression and write recommendations
for the next scheduled workout that contains the same exercise.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics_insight import AnalyticsInsight
from app.models.enums import (
    AnalyticsInsightKind,
    AnalyticsInsightSeverity,
    MovementPattern,
    ProgressionStrategy,
    RecommendationKind,
    ScheduledWorkoutStatus,
    TrackingType,
)
from app.models.exercise import Exercise
from app.models.exercise_progression import ExerciseProgression
from app.models.program import ProgramDay, ProgramDayExercise
from app.models.recommendation import Recommendation
from app.models.scheduled_workout import ScheduledWorkout
from app.models.user_fatigue_state import UserFatigueState
from app.models.workout import WorkoutExercise, WorkoutSession, WorkoutSet
from app.services.progression._types import (
    DoubleInput,
    LinearInput,
    ProgressionDecision,
    ProgressionSet,
    RPEInput,
)
from app.services.progression.double import double_progression
from app.services.progression.linear import linear_progression
from app.services.progression.mesocycle import (
    FATIGUE_THRESHOLD,
    compute_session_fatigue_delta,
)
from app.services.progression.rpe import epley_e1rm, rpe_progression

RPE_INCREMENT_PCT = Decimal("0.025")
RECENT_E1RM_LIMIT = 4

UPPER_MOVEMENT_PATTERNS = {
    MovementPattern.horizontal_push,
    MovementPattern.vertical_push,
    MovementPattern.horizontal_pull,
    MovementPattern.vertical_pull,
    MovementPattern.isolation,
}
LOWER_MOVEMENT_PATTERNS = {
    MovementPattern.squat,
    MovementPattern.hinge,
    MovementPattern.lunge,
}
WEIGHT_BASED_TRACKING = {
    TrackingType.weight_reps,
    TrackingType.weight_reps_distance,
}


def _now() -> datetime:
    return datetime.now(tz=UTC)


def default_increment_kg(movement_pattern: MovementPattern) -> Decimal:
    """Heuristic: 5 kg for lower-body compounds, 2.5 kg for everything else."""
    if movement_pattern in LOWER_MOVEMENT_PATTERNS:
        return Decimal("5")
    return Decimal("2.5")


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


async def _next_scheduled_with_exercise(
    session: AsyncSession,
    user_id: UUID,
    program_id: UUID | None,
    exercise_id: UUID,
    after: datetime,
) -> ScheduledWorkout | None:
    if program_id is None:
        return None
    stmt = (
        select(ScheduledWorkout)
        .join(ProgramDay, ProgramDay.id == ScheduledWorkout.program_day_id)
        .join(ProgramDayExercise, ProgramDayExercise.program_day_id == ProgramDay.id)
        .where(
            ScheduledWorkout.user_id == user_id,
            ScheduledWorkout.program_id == program_id,
            ProgramDayExercise.exercise_id == exercise_id,
            ScheduledWorkout.status == ScheduledWorkoutStatus.planned,
            ScheduledWorkout.scheduled_for >= after.date(),
        )
        .order_by(ScheduledWorkout.scheduled_for)
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def _recent_top_set_e1rms(
    session: AsyncSession,
    *,
    user_id: UUID,
    exercise_id: UUID,
    limit: int = RECENT_E1RM_LIMIT,
) -> list[Decimal]:
    """Top-set e1RM (Epley) from the user's last N completed sessions for the
    given exercise. Newest first."""
    stmt = (
        select(WorkoutExercise.id, WorkoutSession.ended_at)
        .join(WorkoutSession, WorkoutSession.id == WorkoutExercise.workout_session_id)
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutExercise.exercise_id == exercise_id,
            WorkoutSession.ended_at.is_not(None),
            WorkoutSession.deleted_at.is_(None),
        )
        .order_by(WorkoutSession.ended_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    out: list[Decimal] = []
    for we_id, _ in rows:
        sets = (
            (
                await session.execute(
                    select(WorkoutSet).where(WorkoutSet.workout_exercise_id == we_id)
                )
            )
            .scalars()
            .all()
        )
        working = [s for s in sets if s.set_type.value == "working" and s.weight_kg is not None]
        if not working:
            continue
        top_weight = max(s.weight_kg for s in working if s.weight_kg is not None)
        # Best e1RM among sets at the top weight.
        best: Decimal = Decimal(0)
        for s in working:
            if s.weight_kg != top_weight or s.reps is None:
                continue
            e = epley_e1rm(s.weight_kg, s.reps)
            if e > best:
                best = e
        if best > 0:
            out.append(best)
    return out


def _build_progression_sets(sets: list[WorkoutSet]) -> list[ProgressionSet]:
    out: list[ProgressionSet] = []
    for s in sets:
        is_working = s.set_type.value == "working"
        out.append(ProgressionSet(weight_kg=s.weight_kg, reps=s.reps, is_working=is_working))
    return out


def _decision_to_kind(decision: ProgressionDecision, prev_weight: Decimal) -> RecommendationKind:
    if decision.is_deload:
        return RecommendationKind.deload
    if decision.next_weight_kg > prev_weight:
        return RecommendationKind.increase_weight
    if decision.next_weight_kg < prev_weight:
        return RecommendationKind.deload
    # weight held -> increase reps (or hold if reps target unchanged)
    return RecommendationKind.increase_reps


async def _upsert_recommendation(
    session: AsyncSession,
    *,
    user_id: UUID,
    scheduled_workout_id: UUID | None,
    exercise_id: UUID,
    kind: RecommendationKind,
    decision: ProgressionDecision,
    prior_weight_kg: Decimal | None = None,
) -> UUID | None:
    """Upsert the active recommendation row; return its id (or None if the
    upsert was a no-op against a tombstoned row, which shouldn't happen).
    """
    payload = {
        "next_weight_kg": str(decision.next_weight_kg),
        "next_reps_low": decision.next_reps_low,
        "next_reps_high": decision.next_reps_high,
        "is_deload": decision.is_deload,
    }
    if prior_weight_kg is not None:
        payload["prior_weight_kg"] = str(prior_weight_kg)
    values = {
        "user_id": user_id,
        "scheduled_workout_id": scheduled_workout_id,
        "exercise_id": exercise_id,
        "kind": kind.value,
        "payload": payload,
        "rationale_key": decision.rationale_key,
        "suggested_weight_kg": decision.next_weight_kg,
        "suggested_reps_low": decision.next_reps_low,
        "suggested_reps_high": decision.next_reps_high,
        "updated_at": _now(),
    }
    stmt = pg_insert(Recommendation).values(**values)
    # The partial unique index covers active (un-consumed, un-dismissed) recs.
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "scheduled_workout_id", "exercise_id"],
        index_where=(
            (Recommendation.consumed_at.is_(None)) & (Recommendation.dismissed_at.is_(None))
        ),
        set_={
            "kind": stmt.excluded.kind,
            "payload": stmt.excluded.payload,
            "rationale_key": stmt.excluded.rationale_key,
            # Reset stale rationale text whenever the underlying decision changes.
            "rationale": None,
            "suggested_weight_kg": stmt.excluded.suggested_weight_kg,
            "suggested_reps_low": stmt.excluded.suggested_reps_low,
            "suggested_reps_high": stmt.excluded.suggested_reps_high,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    await session.execute(stmt)

    # Newest active rec for this target. With a non-null scheduled_workout_id the
    # partial unique index guarantees at most one; when it is null (no future
    # scheduled session, e.g. a continuous program whose horizon is all in the
    # past) Postgres treats nulls as distinct, so several may accumulate -- take
    # the latest deterministically rather than erroring.
    rec_id = (
        await session.execute(
            select(Recommendation.id)
            .where(
                Recommendation.user_id == user_id,
                Recommendation.exercise_id == exercise_id,
                (
                    Recommendation.scheduled_workout_id == scheduled_workout_id
                    if scheduled_workout_id is not None
                    else Recommendation.scheduled_workout_id.is_(None)
                ),
                Recommendation.consumed_at.is_(None),
                Recommendation.dismissed_at.is_(None),
            )
            .order_by(Recommendation.created_at.desc(), Recommendation.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return rec_id


async def apply_progressions_after_finalize(
    session: AsyncSession, workout: WorkoutSession
) -> list[UUID]:
    """Run after PR detection in finalize_session.

    Returns the list of recommendation row ids that were inserted/updated, so
    the caller can enqueue rationale generation AFTER committing the row.
    Enqueuing pre-commit would race with the worker reading the row.
    """
    if workout.scheduled_workout_id is None:
        return []

    scheduled = (
        await session.execute(
            select(ScheduledWorkout).where(ScheduledWorkout.id == workout.scheduled_workout_id)
        )
    ).scalar_one_or_none()
    if scheduled is None or scheduled.program_day_id is None:
        return []

    # Auto-consume any active rec attached to the just-finished scheduled workout.
    now = _now()
    await session.execute(
        update(Recommendation)
        .where(
            Recommendation.user_id == workout.user_id,
            Recommendation.scheduled_workout_id == scheduled.id,
            Recommendation.consumed_at.is_(None),
            Recommendation.dismissed_at.is_(None),
        )
        .values(consumed_at=now, updated_at=now)
    )

    # Pull all program-day-exercise rows + their workout exercise counterpart.
    pdes = (
        (
            await session.execute(
                select(ProgramDayExercise).where(
                    ProgramDayExercise.program_day_id == scheduled.program_day_id
                )
            )
        )
        .scalars()
        .all()
    )
    if not pdes:
        return []

    over_range_total = 0
    failed_sets_total = 0
    rec_ids: list[UUID] = []

    for pde in pdes:
        if pde.progression_strategy not in (
            ProgressionStrategy.linear,
            ProgressionStrategy.double_progression,
            ProgressionStrategy.rpe_based,
        ):
            continue

        exercise = (
            await session.execute(select(Exercise).where(Exercise.id == pde.exercise_id))
        ).scalar_one()
        if exercise.tracking_type not in WEIGHT_BASED_TRACKING:
            continue

        we = (
            await session.execute(
                select(WorkoutExercise).where(
                    WorkoutExercise.workout_session_id == workout.id,
                    WorkoutExercise.exercise_id == exercise.id,
                )
            )
        ).scalar_one_or_none()
        if we is None:
            continue
        sets = (
            (
                await session.execute(
                    select(WorkoutSet).where(WorkoutSet.workout_exercise_id == we.id)
                )
            )
            .scalars()
            .all()
        )
        if not sets:
            continue

        prog = await _get_or_create_progression(session, workout.user_id, exercise.id)

        # Determine current weight: progression state if known, else the heaviest
        # working set just performed, else 0.
        current_weight = prog.current_top_set_weight_kg
        if current_weight is None:
            working_weights = [
                s.weight_kg
                for s in sets
                if s.set_type.value == "working" and s.weight_kg is not None
            ]
            current_weight = max(working_weights) if working_weights else Decimal("0")

        increment = default_increment_kg(exercise.movement_pattern)
        progression_sets = _build_progression_sets(list(sets))

        # Deload-week short-circuit: hold weight, no progression-engine update.
        if scheduled.is_deload:
            decision = ProgressionDecision(
                next_weight_kg=current_weight,
                next_reps_low=pde.target_reps_low or 5,
                next_reps_high=pde.target_reps_high,
                is_deload=False,
                rationale_key="deload.hold",
                consecutive_failures=prog.consecutive_failures,
                consecutive_successes=prog.consecutive_successes,
                consecutive_above=prog.consecutive_above_range,
            )
            next_scheduled = await _next_scheduled_with_exercise(
                session,
                user_id=workout.user_id,
                program_id=scheduled.program_id,
                exercise_id=exercise.id,
                after=_now(),
            )
            rec_id = await _upsert_recommendation(
                session,
                user_id=workout.user_id,
                scheduled_workout_id=next_scheduled.id if next_scheduled else None,
                exercise_id=exercise.id,
                kind=RecommendationKind.hold,
                decision=decision,
                prior_weight_kg=current_weight,
            )
            if rec_id is not None:
                rec_ids.append(rec_id)
            continue

        if pde.progression_strategy == ProgressionStrategy.linear:
            target_reps = pde.target_reps_low or 5
            decision = linear_progression(
                LinearInput(
                    last_session_sets=progression_sets,
                    target_reps=target_reps,
                    increment_kg=increment,
                    current_weight_kg=current_weight,
                    consecutive_failures=prog.consecutive_failures,
                )
            )
        elif pde.progression_strategy == ProgressionStrategy.double_progression:
            reps_low = pde.target_reps_low or 8
            reps_high = pde.target_reps_high or max(reps_low, 12)
            decision = double_progression(
                DoubleInput(
                    last_session_sets=progression_sets,
                    target_reps_low=reps_low,
                    target_reps_high=reps_high,
                    increment_kg=increment,
                    current_weight_kg=current_weight,
                    consecutive_failures=prog.consecutive_failures,
                )
            )
        else:  # ProgressionStrategy.rpe_based
            reps_low = pde.target_reps_low or 5
            reps_high_optional: int | None = pde.target_reps_high
            rpe_low = pde.target_rpe_low if pde.target_rpe_low is not None else Decimal("7")
            rpe_high = pde.target_rpe_high if pde.target_rpe_high is not None else Decimal("8")
            recent = await _recent_top_set_e1rms(
                session, user_id=workout.user_id, exercise_id=exercise.id
            )
            decision = rpe_progression(
                RPEInput(
                    last_session_sets=progression_sets,
                    set_rpes=[s.rpe for s in sets],
                    set_rirs=[s.rir for s in sets],
                    target_rpe_low=rpe_low,
                    target_rpe_high=rpe_high,
                    target_reps_low=reps_low,
                    target_reps_high=reps_high_optional,
                    increment_pct=RPE_INCREMENT_PCT,
                    current_weight_kg=current_weight,
                    consecutive_above=prog.consecutive_above_range,
                    recent_e1rm=recent,
                )
            )

        prev_weight = current_weight
        prog.current_top_set_weight_kg = decision.next_weight_kg
        prog.current_target_reps_low = decision.next_reps_low
        prog.current_target_reps_high = decision.next_reps_high
        prog.consecutive_failures = decision.consecutive_failures
        prog.consecutive_successes = decision.consecutive_successes
        prog.consecutive_above_range = decision.consecutive_above
        prog.last_updated_at = _now()
        await session.flush()

        # Fatigue signals: rationale "rpe.*above" counts as over-range; any
        # working set with reps < target_reps_low counts as a failed set.
        if decision.rationale_key.startswith("rpe.") and "above" in decision.rationale_key:
            over_range_total += 1
        target_low = pde.target_reps_low
        if target_low is not None:
            for s in sets:
                if s.set_type.value != "working":
                    continue
                if s.reps is not None and s.reps < target_low:
                    failed_sets_total += 1

        next_scheduled = await _next_scheduled_with_exercise(
            session,
            user_id=workout.user_id,
            program_id=scheduled.program_id,
            exercise_id=exercise.id,
            after=_now(),
        )
        kind = _decision_to_kind(decision, prev_weight)
        rec_id = await _upsert_recommendation(
            session,
            user_id=workout.user_id,
            scheduled_workout_id=next_scheduled.id if next_scheduled else None,
            exercise_id=exercise.id,
            kind=kind,
            decision=decision,
            prior_weight_kg=prev_weight,
        )
        if rec_id is not None:
            rec_ids.append(rec_id)

    await _update_fatigue_after_session(
        session,
        user_id=workout.user_id,
        over_range=over_range_total > 0,
        failed_sets=failed_sets_total,
    )

    await session.flush()
    return rec_ids


async def _update_fatigue_after_session(
    session: AsyncSession,
    *,
    user_id: UUID,
    over_range: bool,
    failed_sets: int,
) -> None:
    """Apply a session's fatigue delta and, if the rolling score crosses the
    threshold, write a stagnation insight at severity=action.
    """
    delta = compute_session_fatigue_delta(
        avg_rpe_over_target=over_range,
        failed_working_sets=failed_sets,
    )
    if delta == 0:
        return

    state = (
        await session.execute(select(UserFatigueState).where(UserFatigueState.user_id == user_id))
    ).scalar_one_or_none()
    now = _now()
    if state is None:
        state = UserFatigueState(user_id=user_id, rolling_7d_score=delta, last_event_at=now)
        session.add(state)
    else:
        state.rolling_7d_score = state.rolling_7d_score + delta
        state.last_event_at = now
    await session.flush()

    cooled_down = (
        state.last_insight_at is None or (now - state.last_insight_at).total_seconds() > 86400
    )
    if state.rolling_7d_score >= FATIGUE_THRESHOLD and cooled_down:
        session.add(
            AnalyticsInsight(
                user_id=user_id,
                kind=AnalyticsInsightKind.stagnation,
                severity=AnalyticsInsightSeverity.action,
                title="Consider a deload",
                body=(
                    "Fatigue signals are elevated. Reducing volume and intensity for one "
                    "week typically restores progress."
                ),
                payload={"rolling_7d_score": str(state.rolling_7d_score)},
            )
        )
        state.last_insight_at = now
        await session.flush()
