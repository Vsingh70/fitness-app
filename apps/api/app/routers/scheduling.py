from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.scheduling import (
    ScheduledWorkoutList,
    ScheduledWorkoutUpdate,
    ScheduledWorkoutWithDay,
)
from app.schemas.workout import WorkoutSessionResponse
from app.services import scheduling as svc
from app.services import workouts as workouts_svc

router = APIRouter(tags=["scheduling"])


@router.get("/scheduled-workouts", response_model=ScheduledWorkoutList)
async def list_scheduled_workouts(
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = Query(default=None, alias="to"),
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ScheduledWorkoutList:
    rows = await svc.list_scheduled(session, current_user, from_date=from_, to_date=to)
    return ScheduledWorkoutList(items=[ScheduledWorkoutWithDay.model_validate(r) for r in rows])


@router.patch(
    "/scheduled-workouts/{scheduled_id}",
    response_model=ScheduledWorkoutWithDay,
)
async def patch_scheduled_workout(
    scheduled_id: UUID,
    payload: ScheduledWorkoutUpdate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
    shift_remaining_days: int = Query(default=0, ge=-365, le=365),
) -> ScheduledWorkoutWithDay:
    await svc.update_scheduled(
        session,
        current_user,
        scheduled_id,
        payload,
        shift_remaining_days=shift_remaining_days,
    )
    await session.commit()
    rows = await svc.list_scheduled(session, current_user)
    row = next((r for r in rows if r["id"] == scheduled_id), None)
    if row is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Scheduled workout not found.")
    return ScheduledWorkoutWithDay.model_validate(row)


@router.post(
    "/scheduled-workouts/{scheduled_id}/start",
    response_model=WorkoutSessionResponse,
    status_code=201,
)
async def start_scheduled_workout(
    scheduled_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> WorkoutSessionResponse:
    workout = await svc.start_session_from_scheduled(session, current_user, scheduled_id)
    await session.commit()
    full = await workouts_svc.get_session_full(session, current_user, workout.id)
    return WorkoutSessionResponse.model_validate(full)
