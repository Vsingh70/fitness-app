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

from app.models.enums import (
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
from app.models.workout import WorkoutExercise, WorkoutSession, WorkoutSet
from app.services.progression._types import (
    DoubleInput,
    LinearInput,
    ProgressionDecision,
    ProgressionSet,
)
from app.services.progression.double import double_progression
from app.services.progression.linear import linear_progression

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
) -> None:
    payload = {
        "next_weight_kg": str(decision.next_weight_kg),
        "next_reps_low": decision.next_reps_low,
        "next_reps_high": decision.next_reps_high,
        "is_deload": decision.is_deload,
    }
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
            "suggested_weight_kg": stmt.excluded.suggested_weight_kg,
            "suggested_reps_low": stmt.excluded.suggested_reps_low,
            "suggested_reps_high": stmt.excluded.suggested_reps_high,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    await session.execute(stmt)


async def apply_progressions_after_finalize(session: AsyncSession, workout: WorkoutSession) -> int:
    """Run after PR detection in finalize_session.

    Returns the number of recommendations written/updated.
    """
    if workout.scheduled_workout_id is None:
        return 0

    scheduled = (
        await session.execute(
            select(ScheduledWorkout).where(ScheduledWorkout.id == workout.scheduled_workout_id)
        )
    ).scalar_one_or_none()
    if scheduled is None or scheduled.program_day_id is None:
        return 0

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
        return 0

    written = 0
    for pde in pdes:
        if pde.progression_strategy not in (
            ProgressionStrategy.linear,
            ProgressionStrategy.double_progression,
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

        if pde.progression_strategy == ProgressionStrategy.linear:
            # Use the program target if present, else fall back to 5.
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
        else:
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

        prev_weight = current_weight
        prog.current_top_set_weight_kg = decision.next_weight_kg
        prog.current_target_reps_low = decision.next_reps_low
        prog.current_target_reps_high = decision.next_reps_high
        prog.consecutive_failures = decision.consecutive_failures
        prog.consecutive_successes = decision.consecutive_successes
        prog.last_updated_at = _now()
        await session.flush()

        next_scheduled = await _next_scheduled_with_exercise(
            session,
            user_id=workout.user_id,
            program_id=scheduled.program_id,
            exercise_id=exercise.id,
            after=_now(),
        )
        kind = _decision_to_kind(decision, prev_weight)
        await _upsert_recommendation(
            session,
            user_id=workout.user_id,
            scheduled_workout_id=next_scheduled.id if next_scheduled else None,
            exercise_id=exercise.id,
            kind=kind,
            decision=decision,
        )
        written += 1

    await session.flush()
    return written
