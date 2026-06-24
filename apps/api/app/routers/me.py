from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.export import ExportBundle
from app.schemas.user import MeResponse, MeUpdate, PREventList, PREventResponse
from app.services import prs as prs_svc
from app.services.auth import soft_delete_account
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


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Soft-delete the account with a 7-day grace window.

    Stamps ``deleted_at`` (idempotent) and revokes every refresh token so the
    user is logged out everywhere; subsequent requests with the still-valid
    access token are rejected by ``get_current_user``. A nightly job hard-purges
    the account (and its owned rows) once the grace window elapses.
    """
    await soft_delete_account(session, current_user)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/prs", response_model=PREventList)
async def list_prs(
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = None,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> PREventList:
    items, next_cursor = await prs_svc.list_pr_events(
        session, current_user, limit=limit, cursor=cursor
    )
    return PREventList(
        items=[PREventResponse.model_validate(item) for item in items],
        next_cursor=next_cursor,
    )
