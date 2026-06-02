from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.export import ExportBundle
from app.schemas.user import MeResponse, MeUpdate
from app.services.export import build_export_bundle

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=MeResponse)
async def read_me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse.model_validate(current_user)


@router.get("/export", response_model=ExportBundle)
async def export_me(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ExportBundle:
    """Full account data export (sessions+sets, meals, body metrics, programs)
    as a single JSON bundle for compliance + portability."""
    return await build_export_bundle(session, current_user)


@router.patch("", response_model=MeResponse)
async def update_me(
    body: MeUpdate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MeResponse:
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(current_user, field, value)
    await session.commit()
    await session.refresh(current_user)
    return MeResponse.model_validate(current_user)
