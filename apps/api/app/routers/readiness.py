from datetime import UTC, datetime
from datetime import date as date_cls
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.enums import ScheduledWorkoutStatus
from app.models.scheduled_workout import ScheduledWorkout
from app.models.user import User
from app.schemas.readiness import (
    ReadinessDay,
    ReadinessHistoryResponse,
    ReadinessTodayResponse,
    ReduceTodayVolumeResponse,
    RevertTodayVolumeRequest,
    RevertTodayVolumeResponse,
)
from app.services import readiness as readiness_svc

router = APIRouter(tags=["readiness"])

MAX_HISTORY_DAYS = 365


@router.get("/readiness/today", response_model=ReadinessTodayResponse)
async def readiness_today(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ReadinessTodayResponse:
    today = datetime.now(tz=UTC).date()
    record = await readiness_svc.get_today(session, current_user.id, today=today)
    if record is None or record.readiness_score is None:
        return ReadinessTodayResponse(date=today, score=None, band=None, has_data=False)
    return ReadinessTodayResponse(
        date=record.date,
        score=record.readiness_score,
        band=readiness_svc.severity_band(record.readiness_score),
        has_data=True,
    )


@router.get("/readiness/history", response_model=ReadinessHistoryResponse)
async def readiness_history(
    from_date: date_cls = Query(..., alias="from"),
    to_date: date_cls = Query(..., alias="to"),
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ReadinessHistoryResponse:
    if to_date < from_date:
        raise HTTPException(status_code=400, detail="`to` must be >= `from`.")
    if (to_date - from_date).days > MAX_HISTORY_DAYS:
        raise HTTPException(
            status_code=400, detail=f"Range must be at most {MAX_HISTORY_DAYS} days."
        )
    rows = await readiness_svc.history(
        session, current_user.id, from_date=from_date, to_date=to_date
    )
    items: list[ReadinessDay] = []
    for r in rows:
        items.append(
            ReadinessDay(
                date=r.date,
                score=r.readiness_score,
                band=readiness_svc.severity_band(r.readiness_score)
                if r.readiness_score is not None
                else None,
                steps=r.steps,
                sleep_minutes=r.sleep_minutes,
                resting_hr=r.resting_hr,
                hrv_ms=r.hrv_ms,
            )
        )
    return ReadinessHistoryResponse(items=items)


@router.post("/readiness/reduce-today-volume", response_model=ReduceTodayVolumeResponse)
async def reduce_today_volume(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ReduceTodayVolumeResponse:
    """Flip is_deload=TRUE on today's planned scheduled workouts so the
    progression orchestrator treats them as reduced-volume sessions.

    Returns the list of affected scheduled_workout_ids so the client can pass
    them back to the revert endpoint without touching pre-existing meso-deload
    sessions that happen to land on the same date.
    """
    today = datetime.now(tz=UTC).date()
    affected = (
        (
            await session.execute(
                select(ScheduledWorkout.id).where(
                    ScheduledWorkout.user_id == current_user.id,
                    ScheduledWorkout.scheduled_for == today,
                    ScheduledWorkout.status == ScheduledWorkoutStatus.planned,
                    ScheduledWorkout.is_deload.is_(False),
                )
            )
        )
        .scalars()
        .all()
    )
    if affected:
        await session.execute(
            update(ScheduledWorkout)
            .where(ScheduledWorkout.id.in_(list(affected)))
            .values(is_deload=True)
        )
    await session.commit()
    return ReduceTodayVolumeResponse(
        affected_count=len(affected),
        affected_scheduled_workout_ids=[str(i) for i in affected],
    )


@router.delete(
    "/readiness/reduce-today-volume",
    response_model=RevertTodayVolumeResponse,
)
async def revert_today_volume(
    payload: RevertTodayVolumeRequest,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> RevertTodayVolumeResponse:
    """Revert is_deload to FALSE on the listed scheduled workouts (owned by
    the current user). Client passes back the ids returned by the POST.
    """
    if not payload.scheduled_workout_ids:
        return RevertTodayVolumeResponse(affected_count=0)
    try:
        ids = [UUID(s) for s in payload.scheduled_workout_ids]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_uuid") from exc
    result = await session.execute(
        update(ScheduledWorkout)
        .where(
            ScheduledWorkout.id.in_(ids),
            ScheduledWorkout.user_id == current_user.id,
            ScheduledWorkout.is_deload.is_(True),
        )
        .values(is_deload=False)
    )
    await session.commit()
    return RevertTodayVolumeResponse(affected_count=int(result.rowcount or 0))  # type: ignore[attr-defined]
