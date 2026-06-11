from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.enums import Equipment, MovementPattern, Muscle, TrackingType
from app.models.user import User
from app.schemas.exercise import (
    ExerciseCreate,
    ExerciseList,
    ExerciseResponse,
    ExerciseUpdate,
)
from app.services.exercises import (
    archive_exercise,
    create_exercise,
    delete_exercise,
    get_exercise,
    list_exercises,
    update_exercise,
)

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.get("", response_model=ExerciseList)
async def list_exercises_route(
    q: str | None = None,
    muscle: Muscle | None = None,
    equipment: Equipment | None = None,
    movement_pattern: MovementPattern | None = None,
    tracking_type: TrackingType | None = None,
    mine_only: bool = False,
    include_archived: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = None,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ExerciseList:
    items, next_cursor = await list_exercises(
        session,
        user_id=current_user.id,
        q=q,
        muscle=muscle,
        equipment=equipment,
        movement_pattern=movement_pattern,
        tracking_type=tracking_type,
        mine_only=mine_only,
        include_archived=include_archived,
        limit=limit,
        cursor=cursor,
    )
    return ExerciseList(
        items=[ExerciseResponse.model_validate(item) for item in items],
        next_cursor=next_cursor,
    )


@router.get("/{exercise_id}", response_model=ExerciseResponse)
async def get_exercise_route(
    exercise_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ExerciseResponse:
    exercise = await get_exercise(session, exercise_id, user=current_user)
    return ExerciseResponse.model_validate(exercise)


@router.post("", response_model=ExerciseResponse, status_code=status.HTTP_201_CREATED)
async def create_exercise_route(
    payload: ExerciseCreate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ExerciseResponse:
    exercise = await create_exercise(session, current_user, payload)
    await session.commit()
    await session.refresh(exercise)
    return ExerciseResponse.model_validate(exercise)


@router.patch("/{exercise_id}", response_model=ExerciseResponse)
async def update_exercise_route(
    exercise_id: UUID,
    payload: ExerciseUpdate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ExerciseResponse:
    exercise = await get_exercise(session, exercise_id, user=current_user)
    exercise = await update_exercise(session, exercise, current_user, payload)
    await session.commit()
    await session.refresh(exercise)
    return ExerciseResponse.model_validate(exercise)


@router.post("/{exercise_id}/archive", response_model=ExerciseResponse)
async def archive_exercise_route(
    exercise_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ExerciseResponse:
    exercise = await get_exercise(session, exercise_id, user=current_user)
    exercise = await archive_exercise(session, exercise, current_user)
    await session.commit()
    await session.refresh(exercise)
    return ExerciseResponse.model_validate(exercise)


@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exercise_route(
    exercise_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    exercise = await get_exercise(session, exercise_id, user=current_user)
    await delete_exercise(session, exercise, current_user)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
