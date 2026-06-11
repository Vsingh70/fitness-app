"""Per-exercise analytics deep-dive.

Pulls together time series (e1RM, volume, avg RPE), a set-by-set scatter,
recent PRs, the active progression engine's next-session prediction, and a
rule-based list of variant exercises.

All read-only: no inserts, no recomputation. The orchestrator from 04.01-04.03
keeps `exercise_progression` and `recommendations` fresh; this service just
surfaces those rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RecommendationKind
from app.models.exercise import Exercise
from app.models.exercise_progression import ExerciseProgression
from app.models.recommendation import Recommendation
from app.models.user import User

WindowLiteral = Literal["4w", "8w", "12w", "26w", "52w"]
SUPPORTED_WINDOWS: tuple[str, ...] = ("4w", "8w", "12w", "26w", "52w")
DEFAULT_WINDOW: WindowLiteral = "12w"
SET_SCATTER_LIMIT = 500
RECENT_PR_LIMIT = 5
VARIANT_LIMIT = 10


# Response shapes -----------------------------------------------------------


@dataclass(frozen=True)
class TimeSeriesPoint:
    session_date: date
    value: Decimal


@dataclass(frozen=True)
class ScatterPoint:
    session_date: date
    weight_kg: Decimal
    reps: int
    rpe: Decimal | None
    is_pr: bool


@dataclass(frozen=True)
class PRRow:
    session_date: date
    weight_kg: Decimal
    reps: int
    e1rm_kg: Decimal


@dataclass(frozen=True)
class PredictedNextSession:
    has_prediction: bool
    suggested_weight_kg: Decimal | None
    suggested_reps_low: int | None
    suggested_reps_high: int | None
    kind: RecommendationKind | None
    rationale_key: str | None
    rationale: str | None
    is_deload: bool
    source: str  # "recommendation" | "progression" | "none"


@dataclass(frozen=True)
class ExerciseSummary:
    id: UUID
    name: str
    primary_muscle: str
    secondary_muscles: list[str]
    equipment: str
    movement_pattern: str


@dataclass(frozen=True)
class VariantRow:
    exercise: ExerciseSummary
    usage_count: int


@dataclass(frozen=True)
class ExerciseAnalytics:
    exercise: ExerciseSummary
    window: str
    e1rm_series: list[TimeSeriesPoint]
    volume_series: list[TimeSeriesPoint]
    avg_rpe_series: list[TimeSeriesPoint]
    set_scatter: list[ScatterPoint]
    recent_prs: list[PRRow]
    predicted_next_session: PredictedNextSession
    suggested_variants: list[VariantRow]


# Helpers -------------------------------------------------------------------


def parse_window(value: str | None) -> WindowLiteral:
    """Validate the `window` query string. Default to 12w."""
    if value is None:
        return DEFAULT_WINDOW
    if value not in SUPPORTED_WINDOWS:
        raise HTTPException(
            status_code=400,
            detail=f"`window` must be one of {list(SUPPORTED_WINDOWS)}.",
        )
    return value  # type: ignore[return-value]


def _weeks_for_window(window: WindowLiteral) -> int:
    return int(window.rstrip("w"))


def _today() -> date:
    return datetime.now(tz=UTC).date()


def _epley(weight: Decimal, reps: int) -> Decimal:
    if reps <= 0:
        return Decimal("0")
    factor = Decimal("1") + (Decimal(reps) / Decimal("30"))
    return (weight * factor).quantize(Decimal("0.01"))


# Time-series queries -------------------------------------------------------


async def _per_session_rows(
    session: AsyncSession,
    *,
    user_id: UUID,
    exercise_id: UUID,
    since: date,
) -> tuple[list[tuple[date, list[tuple[Decimal, int, Decimal | None, str]]]], list[PRRow]]:
    """Return (per_session, recent_prs) in one round trip.

    ``per_session`` is [(session_date, [(weight, reps, rpe, set_type), ...])]
    for every ended session in the window that referenced this exercise,
    sorted ascending by session date.

    ``recent_prs`` is the same join filtered to ``is_pr`` sets, newest session
    first, capped at RECENT_PR_LIMIT — derived here instead of a second query.
    """
    rows = (
        await session.execute(
            text(
                """
                SELECT ws.id, ws.started_at, ws.started_at::date,
                       s.weight_kg, s.reps, s.rpe, s.set_type, s.is_pr
                FROM workout_sessions ws
                JOIN workout_exercises we ON we.workout_session_id = ws.id
                JOIN sets s ON s.workout_exercise_id = we.id
                WHERE ws.user_id = :user_id
                  AND we.exercise_id = :exercise_id
                  AND ws.deleted_at IS NULL
                  AND ws.ended_at IS NOT NULL
                  AND ws.started_at::date >= :since
                ORDER BY ws.started_at, ws.id, s.set_index
                """
            ),
            {"user_id": user_id, "exercise_id": exercise_id, "since": since},
        )
    ).all()
    by_session: dict[UUID, tuple[date, list[tuple[Decimal, int, Decimal | None, str]]]] = {}
    pr_raw: list[tuple[datetime, date, Decimal, int]] = []
    for sid, started_at, sdate, weight, reps, rpe, set_type, is_pr in rows:
        entry = by_session.setdefault(sid, (sdate, []))
        if weight is not None and reps is not None:
            entry[1].append((weight, reps, rpe, str(set_type)))
            if is_pr:
                pr_raw.append((started_at, sdate, weight, reps))
    ordered = sorted(by_session.values(), key=lambda x: x[0])

    # Newest session first; the sort is stable so within a session the original
    # set_index order is preserved (matching the old dedicated PR query).
    pr_raw.sort(key=lambda r: r[0], reverse=True)
    prs = [
        PRRow(
            session_date=sdate,
            weight_kg=Decimal(weight),
            reps=int(reps),
            e1rm_kg=_epley(Decimal(weight), int(reps)),
        )
        for (_, sdate, weight, reps) in pr_raw[:RECENT_PR_LIMIT]
    ]
    return ordered, prs


def _build_series(
    per_session: list[tuple[date, list[tuple[Decimal, int, Decimal | None, str]]]],
) -> tuple[list[TimeSeriesPoint], list[TimeSeriesPoint], list[TimeSeriesPoint]]:
    """Build (e1rm_top, volume_tonnage, avg_rpe) series from per-session sets."""
    e1rm_series: list[TimeSeriesPoint] = []
    volume_series: list[TimeSeriesPoint] = []
    rpe_series: list[TimeSeriesPoint] = []
    for sdate, sets in per_session:
        working = [(w, r, rpe) for (w, r, rpe, st) in sets if st == "working"]
        if not working:
            continue
        top_e1rm = max((_epley(w, r) for (w, r, _) in working), default=Decimal("0"))
        tonnage = sum((w * Decimal(r) for (w, r, _) in working), Decimal("0"))
        rpes = [rpe for (_, _, rpe) in working if rpe is not None]
        e1rm_series.append(
            TimeSeriesPoint(session_date=sdate, value=top_e1rm.quantize(Decimal("0.01")))
        )
        volume_series.append(
            TimeSeriesPoint(session_date=sdate, value=tonnage.quantize(Decimal("0.01")))
        )
        if rpes:
            avg = (sum(rpes, Decimal("0")) / Decimal(len(rpes))).quantize(Decimal("0.01"))
            rpe_series.append(TimeSeriesPoint(session_date=sdate, value=avg))
    return e1rm_series, volume_series, rpe_series


def _build_scatter(
    per_session: list[tuple[date, list[tuple[Decimal, int, Decimal | None, str]]]],
    pr_dates: set[tuple[date, Decimal, int]],
) -> list[ScatterPoint]:
    out: list[ScatterPoint] = []
    for sdate, sets in per_session:
        for w, r, rpe, st in sets:
            if st != "working":
                continue
            out.append(
                ScatterPoint(
                    session_date=sdate,
                    weight_kg=w,
                    reps=r,
                    rpe=rpe,
                    is_pr=(sdate, w, r) in pr_dates,
                )
            )
    if len(out) > SET_SCATTER_LIMIT:
        # Keep the most recent N.
        out = out[-SET_SCATTER_LIMIT:]
    return out


# Predicted next session ----------------------------------------------------


async def _predicted_next_session(
    session: AsyncSession, *, user_id: UUID, exercise_id: UUID
) -> PredictedNextSession:
    """Surface the active recommendation row first; fall back to the rolling
    progression state if no active rec exists.
    """
    rec = (
        await session.execute(
            select(Recommendation)
            .where(
                Recommendation.user_id == user_id,
                Recommendation.exercise_id == exercise_id,
                Recommendation.consumed_at.is_(None),
                Recommendation.dismissed_at.is_(None),
            )
            .order_by(Recommendation.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if rec is not None:
        is_deload = bool(rec.payload.get("is_deload")) if rec.payload else False
        return PredictedNextSession(
            has_prediction=True,
            suggested_weight_kg=rec.suggested_weight_kg,
            suggested_reps_low=rec.suggested_reps_low,
            suggested_reps_high=rec.suggested_reps_high,
            kind=rec.kind,
            rationale_key=rec.rationale_key,
            rationale=rec.rationale,
            is_deload=is_deload,
            source="recommendation",
        )

    prog = (
        await session.execute(
            select(ExerciseProgression).where(
                ExerciseProgression.user_id == user_id,
                ExerciseProgression.exercise_id == exercise_id,
            )
        )
    ).scalar_one_or_none()
    if prog is None or prog.current_top_set_weight_kg is None:
        return PredictedNextSession(
            has_prediction=False,
            suggested_weight_kg=None,
            suggested_reps_low=None,
            suggested_reps_high=None,
            kind=None,
            rationale_key=None,
            rationale=None,
            is_deload=False,
            source="none",
        )
    return PredictedNextSession(
        has_prediction=True,
        suggested_weight_kg=prog.current_top_set_weight_kg,
        suggested_reps_low=prog.current_target_reps_low,
        suggested_reps_high=prog.current_target_reps_high,
        kind=None,
        rationale_key=None,
        rationale=None,
        is_deload=False,
        source="progression",
    )


# Variants ------------------------------------------------------------------


async def _suggested_variants(
    session: AsyncSession, *, user: User, exercise: Exercise
) -> list[VariantRow]:
    """Same primary muscle, same movement pattern, different equipment.

    Public catalog + the user's own custom exercises; excludes archived.
    Ranked by usage count descending, then by name ascending.
    """
    from app.models.workout import WorkoutExercise, WorkoutSession

    # Only count usage for plausible variant candidates (same muscle + pattern)
    # instead of aggregating over the user's entire workout history.
    candidate_ids = select(Exercise.id).where(
        Exercise.primary_muscle == exercise.primary_muscle,
        Exercise.movement_pattern == exercise.movement_pattern,
    )

    usage_subq = (
        select(
            WorkoutExercise.exercise_id.label("exercise_id"),
            func.count().label("usage"),
        )
        .join(WorkoutSession, WorkoutSession.id == WorkoutExercise.workout_session_id)
        .where(
            WorkoutSession.user_id == user.id,
            WorkoutSession.deleted_at.is_(None),
            WorkoutExercise.exercise_id.in_(candidate_ids.scalar_subquery()),
        )
        .group_by(WorkoutExercise.exercise_id)
        .subquery("usage_subq")
    )

    stmt = (
        select(Exercise, func.coalesce(usage_subq.c.usage, 0).label("usage"))
        .outerjoin(usage_subq, usage_subq.c.exercise_id == Exercise.id)
        .where(
            Exercise.id != exercise.id,
            Exercise.primary_muscle == exercise.primary_muscle,
            Exercise.movement_pattern == exercise.movement_pattern,
            Exercise.equipment != exercise.equipment,
            Exercise.archived_at.is_(None),
            (Exercise.owner_id.is_(None)) | (Exercise.owner_id == user.id),
        )
        .order_by(func.coalesce(usage_subq.c.usage, 0).desc(), Exercise.name.asc())
        .limit(VARIANT_LIMIT)
    )
    rows = (await session.execute(stmt)).all()
    out: list[VariantRow] = []
    for ex, usage in rows:
        out.append(
            VariantRow(
                exercise=ExerciseSummary(
                    id=ex.id,
                    name=ex.name,
                    primary_muscle=str(ex.primary_muscle.value),
                    secondary_muscles=[str(m.value) for m in ex.secondary_muscles],
                    equipment=str(ex.equipment.value),
                    movement_pattern=str(ex.movement_pattern.value),
                ),
                usage_count=int(usage or 0),
            )
        )
    return out


# Orchestrator --------------------------------------------------------------


async def build_exercise_analytics(
    session: AsyncSession,
    *,
    user: User,
    exercise_id: UUID,
    window: WindowLiteral,
    today: date | None = None,
) -> ExerciseAnalytics:
    today = today or _today()
    weeks = _weeks_for_window(window)
    since = today - timedelta(weeks=weeks)

    exercise = (
        await session.execute(select(Exercise).where(Exercise.id == exercise_id))
    ).scalar_one_or_none()
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found.")
    if exercise.owner_id is not None and exercise.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Exercise not found.")

    per_session, prs = await _per_session_rows(
        session, user_id=user.id, exercise_id=exercise_id, since=since
    )
    e1rm_series, volume_series, rpe_series = _build_series(per_session)

    pr_keys = {(p.session_date, p.weight_kg, p.reps) for p in prs}
    scatter = _build_scatter(per_session, pr_keys)

    predicted = await _predicted_next_session(session, user_id=user.id, exercise_id=exercise_id)
    variants = await _suggested_variants(session, user=user, exercise=exercise)

    summary = ExerciseSummary(
        id=exercise.id,
        name=exercise.name,
        primary_muscle=str(exercise.primary_muscle.value),
        secondary_muscles=[str(m.value) for m in exercise.secondary_muscles],
        equipment=str(exercise.equipment.value),
        movement_pattern=str(exercise.movement_pattern.value),
    )

    return ExerciseAnalytics(
        exercise=summary,
        window=window,
        e1rm_series=e1rm_series,
        volume_series=volume_series,
        avg_rpe_series=rpe_series,
        set_scatter=scatter,
        recent_prs=prs,
        predicted_next_session=predicted,
        suggested_variants=variants,
    )
