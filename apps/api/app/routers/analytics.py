from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.enums import Muscle
from app.models.user import User
from app.schemas.analytics import (
    CurrentWeekMusclePoint,
    CurrentWeekResponse,
    VolumePoint,
    VolumeResponse,
    VolumeSeries,
)
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
