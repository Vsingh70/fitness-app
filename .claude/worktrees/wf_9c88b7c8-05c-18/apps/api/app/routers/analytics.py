from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.enums import Equipment, MovementPattern, Muscle
from app.models.user import User
from app.schemas.analytics import (
    CurrentWeekMusclePoint,
    CurrentWeekResponse,
    ExerciseAnalyticsResponse,
    ExerciseSummaryResponse,
    PredictedNextSessionResponse,
    PRRowResponse,
    ScatterPointResponse,
    TimeSeriesPointResponse,
    VariantRowResponse,
    VolumePoint,
    VolumeResponse,
    VolumeSeries,
)
from app.services.analytics import exercise_analytics as exercise_svc
from app.services.analytics import volume as svc

router = APIRouter(tags=["analytics"], prefix="/analytics")

MAX_WEEKS = 52


def _iso_week_distance(start: date, end: date) -> int:
    """Number of ISO weeks between two dates (inclusive)."""
    return ((end - start).days // 7) + 1


@router.get("/volume", response_model=VolumeResponse)
async def get_volume(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> VolumeResponse:
    if to_date < from_date:
        raise HTTPException(status_code=400, detail="`to` must be >= `from`.")
    if _iso_week_distance(from_date, to_date) > MAX_WEEKS:
        raise HTTPException(status_code=400, detail=f"Range must be at most {MAX_WEEKS} weeks.")
    from_year, from_week, _ = from_date.isocalendar()
    to_year, to_week, _ = to_date.isocalendar()

    by_muscle = await svc.fetch_series(
        session,
        user_id=current_user.id,
        from_year=from_year,
        from_week=from_week,
        to_year=to_year,
        to_week=to_week,
    )

    items: list[VolumeSeries] = []
    for muscle_str, points in by_muscle.items():
        items.append(
            VolumeSeries(
                muscle=Muscle(muscle_str),
                points=[
                    VolumePoint(
                        iso_year=p.iso_year,
                        iso_week=p.iso_week,
                        working_sets=p.working_sets,
                        tonnage_kg=p.tonnage_kg,
                        average_rir=p.average_rir,
                    )
                    for p in points
                ],
            )
        )
    return VolumeResponse(items=items)


@router.get("/exercises/{exercise_id}", response_model=ExerciseAnalyticsResponse)
async def get_exercise_analytics(
    exercise_id: UUID,
    window: str | None = Query(default=None),
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ExerciseAnalyticsResponse:
    parsed = exercise_svc.parse_window(window)
    data = await exercise_svc.build_exercise_analytics(
        session, user=current_user, exercise_id=exercise_id, window=parsed
    )
    return ExerciseAnalyticsResponse(
        exercise=ExerciseSummaryResponse(
            id=data.exercise.id,
            name=data.exercise.name,
            primary_muscle=Muscle(data.exercise.primary_muscle),
            secondary_muscles=[Muscle(m) for m in data.exercise.secondary_muscles],
            equipment=Equipment(data.exercise.equipment),
            movement_pattern=MovementPattern(data.exercise.movement_pattern),
        ),
        window=data.window,
        e1rm_series=[
            TimeSeriesPointResponse(session_date=p.session_date, value=p.value)
            for p in data.e1rm_series
        ],
        volume_series=[
            TimeSeriesPointResponse(session_date=p.session_date, value=p.value)
            for p in data.volume_series
        ],
        avg_rpe_series=[
            TimeSeriesPointResponse(session_date=p.session_date, value=p.value)
            for p in data.avg_rpe_series
        ],
        set_scatter=[
            ScatterPointResponse(
                session_date=s.session_date,
                weight_kg=s.weight_kg,
                reps=s.reps,
                rpe=s.rpe,
                is_pr=s.is_pr,
            )
            for s in data.set_scatter
        ],
        recent_prs=[
            PRRowResponse(
                session_date=r.session_date,
                weight_kg=r.weight_kg,
                reps=r.reps,
                e1rm_kg=r.e1rm_kg,
            )
            for r in data.recent_prs
        ],
        predicted_next_session=PredictedNextSessionResponse(
            has_prediction=data.predicted_next_session.has_prediction,
            suggested_weight_kg=data.predicted_next_session.suggested_weight_kg,
            suggested_reps_low=data.predicted_next_session.suggested_reps_low,
            suggested_reps_high=data.predicted_next_session.suggested_reps_high,
            kind=data.predicted_next_session.kind,
            rationale_key=data.predicted_next_session.rationale_key,
            rationale=data.predicted_next_session.rationale,
            is_deload=data.predicted_next_session.is_deload,
            source=data.predicted_next_session.source,
        ),
        suggested_variants=[
            VariantRowResponse(
                exercise=ExerciseSummaryResponse(
                    id=v.exercise.id,
                    name=v.exercise.name,
                    primary_muscle=Muscle(v.exercise.primary_muscle),
                    secondary_muscles=[Muscle(m) for m in v.exercise.secondary_muscles],
                    equipment=Equipment(v.exercise.equipment),
                    movement_pattern=MovementPattern(v.exercise.movement_pattern),
                ),
                usage_count=v.usage_count,
            )
            for v in data.suggested_variants
        ],
    )


@router.get("/volume/current-week", response_model=CurrentWeekResponse)
async def get_volume_current_week(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> CurrentWeekResponse:
    today = datetime.now(tz=UTC).date()
    summary = await svc.fetch_current_week_summary(session, user_id=current_user.id, today=today)
    return CurrentWeekResponse(
        iso_year=summary.iso_year,
        iso_week=summary.iso_week,
        total_working_sets=summary.total_working_sets,
        total_tonnage_kg=summary.total_tonnage_kg,
        per_muscle=[
            CurrentWeekMusclePoint(
                muscle=Muscle(p.muscle),
                working_sets=p.working_sets,
                tonnage_kg=p.tonnage_kg,
            )
            for p in summary.per_muscle
        ],
    )
