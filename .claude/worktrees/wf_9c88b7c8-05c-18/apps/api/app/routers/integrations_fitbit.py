import base64
import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.integrations_fitbit import (
    FitbitAuthorizeRequest,
    FitbitAuthorizeResponse,
    FitbitCallbackRequest,
    FitbitStatusResponse,
    FitbitSyncResponse,
)
from app.services import fitbit_oauth, fitbit_sync
from app.services.fitbit_oauth_enqueue import enqueue_sync_for_fitbit_user

router = APIRouter(tags=["integrations-fitbit"])

logger = logging.getLogger(__name__)


@router.post(
    "/integrations/fitbit/authorize",
    response_model=FitbitAuthorizeResponse,
)
async def fitbit_authorize(
    payload: FitbitAuthorizeRequest,
    current_user: User = Depends(get_current_user),
) -> FitbitAuthorizeResponse:
    result = fitbit_oauth.build_authorize(
        current_user,
        code_challenge=payload.code_challenge,
        scopes=payload.scopes,
    )
    return FitbitAuthorizeResponse(authorize_url=result.authorize_url, state=result.state)


@router.post("/integrations/fitbit/callback", response_model=FitbitStatusResponse)
async def fitbit_callback(
    payload: FitbitCallbackRequest,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> FitbitStatusResponse:
    connection = await fitbit_oauth.complete_callback(
        session,
        current_user,
        code=payload.code,
        state=payload.state,
        code_verifier=payload.code_verifier,
    )
    await session.commit()
    return FitbitStatusResponse(
        connected=True,
        last_synced_at=connection.last_synced_at,
        last_synced_activity_at=connection.last_synced_activity_at,
        scopes=list(connection.scopes),
    )


@router.delete("/integrations/fitbit", status_code=status.HTTP_204_NO_CONTENT)
async def fitbit_disconnect(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    await fitbit_oauth.disconnect(session, current_user)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/integrations/fitbit/status", response_model=FitbitStatusResponse)
async def fitbit_status(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> FitbitStatusResponse:
    connection = await fitbit_oauth.get_connection(session, current_user)
    if connection is None:
        return FitbitStatusResponse(connected=False, scopes=[])
    return FitbitStatusResponse(
        connected=True,
        last_synced_at=connection.last_synced_at,
        last_synced_activity_at=connection.last_synced_activity_at,
        scopes=list(connection.scopes),
    )


@router.post("/integrations/fitbit/sync", response_model=FitbitSyncResponse)
async def fitbit_sync_now(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> FitbitSyncResponse:
    result = await fitbit_sync.sync_user(session, current_user.id)
    await session.commit()
    return FitbitSyncResponse(
        activities_written=result.activities_written,
        daily_metrics_written=result.daily_metrics_written,
    )


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------


@router.get("/webhooks/fitbit")
async def fitbit_webhook_verify(
    verify: str = Query(...),
) -> Response:
    """Fitbit subscriber verification: returns 204 if `verify` matches the
    configured code, otherwise 404 (per Fitbit docs).
    """
    expected = get_settings().fitbit_webhook_subscriber_verification
    if hmac.compare_digest(verify, expected):
        return Response(status_code=204)
    raise HTTPException(status_code=404, detail="not_found")


@router.post("/webhooks/fitbit")
async def fitbit_webhook(
    request: Request,
    x_fitbit_signature: str | None = Header(default=None, alias="X-Fitbit-Signature"),
) -> Response:
    """Receive a Fitbit notification, verify signature, enqueue sync_user
    for each affected ownerId. Body is a JSON array of subscription events.
    """
    body = await request.body()
    secret = get_settings().fitbit_webhook_signing_secret
    if secret:
        if x_fitbit_signature is None:
            raise HTTPException(status_code=401, detail="missing_signature")
        computed = hmac.new(secret.encode("utf-8"), body, hashlib.sha1).digest()
        expected = base64.b64encode(computed).decode("ascii")
        if not hmac.compare_digest(expected, x_fitbit_signature):
            raise HTTPException(status_code=401, detail="invalid_signature")

    # Decode + dispatch is best-effort; we enqueue an ARQ sync job per ownerId.
    # Failure to enqueue logs and continues so Fitbit doesn't see a 5xx and
    # disable our subscriber.
    try:
        events = json.loads(body)
    except json.JSONDecodeError:
        logger.warning("fitbit_webhook_bad_json")
        return Response(status_code=204)

    if isinstance(events, list):
        for event in events:
            if not isinstance(event, dict):
                continue
            owner = event.get("ownerId")
            if owner:
                try:
                    await enqueue_sync_for_fitbit_user(str(owner))
                except Exception as exc:  # noqa: BLE001
                    logger.warning("fitbit_webhook_enqueue_failed", extra={"error": repr(exc)})

    return Response(status_code=204)
