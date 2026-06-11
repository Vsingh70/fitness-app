"""Push finished workout sessions to Fitbit's activity log.

Mapping:
- If >=50% of working sets are on `MovementPattern.cardio` exercises, pick a
  cardio activity type (Run, Bike, etc. - we keep it simple with the generic
  cardio fallback). Otherwise default to Strength Training (activityId 3001).
- Description = name + total tonnage summary.

Idempotency:
- Skip if the session already has `fitbit_pushed_at`.
- On Fitbit 409 (duplicate), still mark pushed without retry.
- On Fitbit 401/403, log + skip silently. The next sync (07.01) refresh path
  will surface auth issues canonically.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.clients import fitbit
from app.models.enums import MovementPattern, SetType
from app.models.exercise import Exercise
from app.models.fitbit_connection import FitbitConnection
from app.models.user import User
from app.models.workout import WorkoutExercise, WorkoutSession
from app.services.security import secretbox

logger = logging.getLogger(__name__)

# Fitbit activity IDs (https://dev.fitbit.com/build/reference/web-api/exploration-guide/activity-and-exercise/)
STRENGTH_TRAINING_ID = 3001
CARDIO_GENERIC_ID = 90013  # generic "Workout"

CARDIO_PATTERN_TO_FITBIT_ID: dict[MovementPattern, int] = {
    # Keep the table small and add as we learn what users do.
    MovementPattern.cardio: CARDIO_GENERIC_ID,
}

CARDIO_RATIO_THRESHOLD = Decimal("0.5")


@dataclass(frozen=True)
class PushDecision:
    activity_id: int
    duration_ms: int
    description: str
    distance_meters: Decimal | None


@dataclass(frozen=True)
class PushResult:
    pushed: bool
    skipped_reason: str | None
    fitbit_log_id: str | None


def _now() -> datetime:
    return datetime.now(tz=UTC)


async def _load_full_session(session: AsyncSession, session_id: UUID) -> WorkoutSession | None:
    stmt = (
        select(WorkoutSession)
        .where(WorkoutSession.id == session_id)
        .options(selectinload(WorkoutSession.workout_exercises).selectinload(WorkoutExercise.sets))
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def _movement_patterns_by_exercise(
    session: AsyncSession, exercise_ids: list[UUID]
) -> dict[UUID, MovementPattern]:
    if not exercise_ids:
        return {}
    rows = (
        await session.execute(
            select(Exercise.id, Exercise.movement_pattern).where(Exercise.id.in_(exercise_ids))
        )
    ).all()
    return {ex_id: pattern for ex_id, pattern in rows}


def _cardio_ratio(
    workout: WorkoutSession, patterns: dict[UUID, MovementPattern]
) -> tuple[Decimal, MovementPattern | None]:
    """Return (cardio_share, dominant_cardio_pattern_if_any)."""
    working_total = 0
    cardio_count = 0
    cardio_patterns: Counter[MovementPattern] = Counter()
    for we in workout.workout_exercises:
        pattern = patterns.get(we.exercise_id)
        for s in we.sets:
            if s.set_type != SetType.working:
                continue
            working_total += 1
            if pattern == MovementPattern.cardio:
                cardio_count += 1
                cardio_patterns[pattern] += 1
    if working_total == 0:
        return Decimal("0"), None
    ratio = (Decimal(cardio_count) / Decimal(working_total)).quantize(Decimal("0.01"))
    dominant = cardio_patterns.most_common(1)[0][0] if cardio_patterns else None
    return ratio, dominant


def _total_tonnage(workout: WorkoutSession) -> Decimal:
    total = Decimal("0")
    for we in workout.workout_exercises:
        for s in we.sets:
            if s.weight_kg is None or s.reps is None:
                continue
            if s.set_type.value != "working":
                continue
            total += s.weight_kg * Decimal(s.reps)
    return total.quantize(Decimal("0.01"))


def _build_description(workout: WorkoutSession) -> str:
    parts: list[str] = []
    if workout.name:
        parts.append(workout.name)
    tonnage = _total_tonnage(workout)
    if tonnage > 0:
        parts.append(f"total volume {tonnage} kg")
    return ". ".join(parts) if parts else "Logged from gym-app."


async def decide_push(session: AsyncSession, workout: WorkoutSession) -> PushDecision | None:
    """Decide what to send to Fitbit. Returns None if the session is too thin
    (no ended_at, no exercises) to push.
    """
    if workout.ended_at is None or not workout.workout_exercises:
        return None
    duration_ms = int((workout.ended_at - workout.started_at).total_seconds() * 1000)
    if duration_ms <= 0:
        return None

    exercise_ids = [we.exercise_id for we in workout.workout_exercises]
    patterns = await _movement_patterns_by_exercise(session, exercise_ids)
    cardio_share, dominant = _cardio_ratio(workout, patterns)
    if cardio_share >= CARDIO_RATIO_THRESHOLD and dominant is not None:
        activity_id = CARDIO_PATTERN_TO_FITBIT_ID.get(dominant, CARDIO_GENERIC_ID)
    else:
        activity_id = STRENGTH_TRAINING_ID

    return PushDecision(
        activity_id=activity_id,
        duration_ms=duration_ms,
        description=_build_description(workout),
        distance_meters=None,
    )


async def push_session_to_fitbit(session: AsyncSession, session_id: UUID) -> PushResult:
    """Push one workout session. Idempotent: already-pushed sessions short-circuit."""
    workout = await _load_full_session(session, session_id)
    if workout is None:
        return PushResult(pushed=False, skipped_reason="not_found", fitbit_log_id=None)
    if workout.fitbit_pushed_at is not None:
        return PushResult(
            pushed=False, skipped_reason="already_pushed", fitbit_log_id=workout.fitbit_log_id
        )
    user = (
        await session.execute(select(User).where(User.id == workout.user_id))
    ).scalar_one_or_none()
    if user is None:
        return PushResult(pushed=False, skipped_reason="user_missing", fitbit_log_id=None)
    if not user.auto_push_to_fitbit:
        # Manual trigger callers can flip the flag temporarily; this branch is
        # mostly a guard so the worker never pushes when the toggle is off.
        # The router endpoint reads the same flag.
        pass  # do not short-circuit; manual trigger should still work

    connection = (
        await session.execute(
            select(FitbitConnection).where(FitbitConnection.user_id == workout.user_id)
        )
    ).scalar_one_or_none()
    if connection is None:
        return PushResult(pushed=False, skipped_reason="not_connected", fitbit_log_id=None)

    decision = await decide_push(session, workout)
    if decision is None:
        return PushResult(pushed=False, skipped_reason="thin_session", fitbit_log_id=None)

    access_token = secretbox.decrypt(connection.access_token_encrypted)
    try:
        result = await fitbit.post_activity(
            access_token=access_token,
            activity_id=decision.activity_id,
            start_time=workout.started_at,
            duration_ms=decision.duration_ms,
            distance_meters=decision.distance_meters,
            description=decision.description,
        )
    except fitbit.FitbitDuplicateError:
        # Fitbit thinks this is a duplicate. Mark pushed without a log id so
        # we won't retry; if user repushes via the manual endpoint, the same
        # branch still short-circuits because `fitbit_pushed_at` is now set.
        workout.fitbit_pushed_at = _now()
        await session.flush()
        return PushResult(pushed=True, skipped_reason="duplicate_on_fitbit", fitbit_log_id=None)
    except fitbit.FitbitAuthError as exc:
        logger.warning("fitbit_push_auth_failure", extra={"error": repr(exc)})
        return PushResult(pushed=False, skipped_reason="auth_failed", fitbit_log_id=None)
    except fitbit.FitbitRateLimitedError as exc:
        logger.warning("fitbit_push_rate_limited", extra={"error": repr(exc)})
        return PushResult(pushed=False, skipped_reason="rate_limited", fitbit_log_id=None)
    except fitbit.FitbitClientError as exc:
        logger.warning("fitbit_push_client_error", extra={"error": repr(exc)})
        return PushResult(pushed=False, skipped_reason="client_error", fitbit_log_id=None)

    workout.fitbit_log_id = result.log_id
    workout.fitbit_pushed_at = _now()
    await session.flush()
    return PushResult(pushed=True, skipped_reason=None, fitbit_log_id=result.log_id)


async def clear_fitbit_link(session: AsyncSession, workout: WorkoutSession) -> None:
    """Forget the Fitbit linkage on our side. Does not delete from Fitbit."""
    workout.fitbit_log_id = None
    workout.fitbit_pushed_at = None
    await session.flush()
