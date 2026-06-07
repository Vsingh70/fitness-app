"""Google Health integration router (Fitbit account via Google).

OAuth connect/callback/status + disconnect, plus a /sync that pulls body
measurements (weight, body-fat) into body_metrics.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.google_health import GoogleHealthAuthError
from app.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.integrations_health import (
    HealthAuthorizeRequest,
    HealthAuthorizeResponse,
    HealthCallbackRequest,
    HealthProbeEntry,
    HealthProbeResponse,
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
        needs_reauth=connection.needs_reauth,
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
        needs_reauth=connection.needs_reauth,
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
    try:
        result = await health_sync.sync_user(session, current_user.id)
    except GoogleHealthAuthError:
        # sync_user flagged the connection needs_reauth; persist that and tell the
        # client to prompt a reconnect (409 rather than a generic 500).
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reconnect required: the Fitbit (Google Health) authorization has expired.",
        ) from None
    await session.commit()
    return HealthSyncResponse(
        weight_written=result.weight_written,
        body_fat_written=result.body_fat_written,
        daily_metrics_written=result.daily_metrics_written,
    )


# TEMPORARY (spike): discover whether Google exposes ECG + its dataType ID/shape.
# Trigger once after re-consenting to the ECG scope; read results from the server
# log (PROBE_SHAPE lines). Remove after the build-vs-revert decision.
@router.post("/integrations/health/probe-ecg", response_model=HealthProbeResponse)
async def health_probe_ecg(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> HealthProbeResponse:
    results = await health_sync.probe_ecg_user(session, current_user.id)
    return HealthProbeResponse(
        results=[
            HealthProbeEntry(
                data_type=r.data_type,
                status=r.status,
                ok=r.ok,
                point_count=r.point_count,
                sample=r.sample,
                error=r.error,
            )
            for r in results
        ]
    )
