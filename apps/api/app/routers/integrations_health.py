"""Google Health integration router (Fitbit account via Google).

OAuth connect/callback/status + disconnect, plus a /sync that pulls body
measurements (weight, body-fat) into body_metrics.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.integrations_health import (
    HealthAuthorizeRequest,
    HealthAuthorizeResponse,
    HealthCallbackRequest,
    HealthStatusResponse,
    HealthSyncResponse,
)
from app.services import health_oauth, health_sync

router = APIRouter(tags=["integrations-health"])

logger = logging.getLogger(__name__)


@router.post(
    "/integrations/health/authorize",
    response_model=HealthAuthorizeResponse,
)
async def health_authorize(
    payload: HealthAuthorizeRequest,
    current_user: User = Depends(get_current_user),
) -> HealthAuthorizeResponse:
    result = health_oauth.build_authorize(
        current_user,
        code_challenge=payload.code_challenge,
        scopes=payload.scopes,
    )
    return HealthAuthorizeResponse(authorize_url=result.authorize_url, state=result.state)


@router.post("/integrations/health/callback", response_model=HealthStatusResponse)
async def health_callback(
    payload: HealthCallbackRequest,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> HealthStatusResponse:
    connection = await health_oauth.complete_callback(
        session,
        current_user,
        code=payload.code,
        state=payload.state,
        code_verifier=payload.code_verifier,
    )
    await session.commit()
    return HealthStatusResponse(
        connected=True,
        last_synced_at=connection.last_synced_at,
        last_synced_activity_at=connection.last_synced_activity_at,
        scopes=list(connection.scopes),
    )


@router.get("/integrations/health/status", response_model=HealthStatusResponse)
async def health_status(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> HealthStatusResponse:
    connection = await health_oauth.get_connection(session, current_user)
    if connection is None:
        return HealthStatusResponse(connected=False, scopes=[])
    return HealthStatusResponse(
        connected=True,
        last_synced_at=connection.last_synced_at,
        last_synced_activity_at=connection.last_synced_activity_at,
        scopes=list(connection.scopes),
    )


@router.delete("/integrations/health", status_code=status.HTTP_204_NO_CONTENT)
async def health_disconnect(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    await health_oauth.disconnect(session, current_user)
    await session.commit()


@router.post("/integrations/health/sync", response_model=HealthSyncResponse)
async def health_sync_now(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> HealthSyncResponse:
    """Pull weight + body-fat into body_metrics and steps/HR/HRV/sleep into
    daily_metrics from the connected account."""
    result = await health_sync.sync_user(session, current_user.id)
    await session.commit()
    return HealthSyncResponse(
        weight_written=result.weight_written,
        body_fat_written=result.body_fat_written,
        daily_metrics_written=result.daily_metrics_written,
    )
