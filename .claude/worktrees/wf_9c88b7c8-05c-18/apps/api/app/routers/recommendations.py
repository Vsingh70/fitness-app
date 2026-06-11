from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.recommendation import RecommendationList, RecommendationResponse
from app.services import recommendations as svc

router = APIRouter(tags=["recommendations"])


@router.get("/recommendations", response_model=RecommendationList)
async def list_recommendations(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> RecommendationList:
    rows = await svc.list_active(session, current_user)
    return RecommendationList(items=[RecommendationResponse.model_validate(r) for r in rows])


@router.get(
    "/scheduled-workouts/{scheduled_id}/recommendations",
    response_model=RecommendationList,
)
async def list_recommendations_for_scheduled(
    scheduled_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> RecommendationList:
    rows = await svc.list_for_scheduled(session, current_user, scheduled_id)
    return RecommendationList(items=[RecommendationResponse.model_validate(r) for r in rows])


@router.post("/recommendations/{rec_id}/consume", response_model=RecommendationResponse)
async def consume_recommendation(
    rec_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> RecommendationResponse:
    record = await svc.consume(session, current_user, rec_id)
    await session.commit()
    return RecommendationResponse.model_validate(record)


@router.post("/recommendations/{rec_id}/dismiss", response_model=RecommendationResponse)
async def dismiss_recommendation(
    rec_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> RecommendationResponse:
    record = await svc.dismiss(session, current_user, rec_id)
    await session.commit()
    return RecommendationResponse.model_validate(record)
