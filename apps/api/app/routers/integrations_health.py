"""Google Health integration router (Phase 1 spike).

Mirrors ``routers/integrations_fitbit.py`` for the OAuth surface, plus a
TEMPORARY ``/probe`` endpoint: after the user connects once, hitting /probe with
the stored access token reveals the real Google Health data-API response shapes,
which is exactly what this spike exists to discover for Phase 2.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import google_health
from app.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.integrations_health import (
    HealthAuthorizeRequest,
    HealthAuthorizeResponse,
    HealthCallbackRequest,
    HealthProbeEntry,
    HealthProbeResponse,
    HealthStatusResponse,
)
from app.services import health_oauth
from app.services.security import secretbox

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


@router.post("/integrations/health/probe", response_model=HealthProbeResponse)
async def health_probe(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> HealthProbeResponse:
    """TEMPORARY (spike): probe candidate Google Health data endpoints with the
    stored access token and return the raw results so we can learn the real API
    shape. Remove before Phase 2 ships.
    """
    connection = await health_oauth.get_connection(session, current_user)
    if connection is None:
        raise HTTPException(status_code=400, detail="not_connected")
    access_token = secretbox.decrypt(connection.access_token_encrypted)
    results = await google_health.probe_data(access_token=access_token)
    return HealthProbeResponse(
        results=[
            HealthProbeEntry(
                label=r.label,
                method=r.method,
                url=r.url,
                status=r.status,
                ok=r.ok,
                body_snippet=r.body_snippet,
                error=r.error,
            )
            for r in results
        ]
    )
