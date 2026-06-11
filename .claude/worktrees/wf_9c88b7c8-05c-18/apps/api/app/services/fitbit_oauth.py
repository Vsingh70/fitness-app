"""Fitbit OAuth orchestration: authorize URL + state JWT, callback exchange,
disconnect with revoke.

PKCE: the client (web or iOS) generates a random `code_verifier`, hashes it
into `code_challenge`, and stores the verifier locally. We just pass the
challenge into the authorize URL and accept the verifier on callback.

The state token is a short-lived JWT signed with the existing JWT_SECRET so
the callback can verify it without server-side state.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import fitbit
from app.config import get_settings
from app.models.fitbit_connection import FitbitConnection
from app.models.user import User
from app.services.security import secretbox

DEFAULT_SCOPES = ["activity", "heartrate", "sleep", "weight", "profile"]
STATE_TTL_SECONDS = 300


@dataclass(frozen=True)
class AuthorizePayload:
    authorize_url: str
    state: str


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _state_jwt(user_id: UUID) -> str:
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "purpose": "fitbit_oauth_state",
        "nonce": secrets.token_urlsafe(16),
        "exp": int((_now() + timedelta(seconds=STATE_TTL_SECONDS)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _verify_state(state: str, user_id: UUID) -> None:
    settings = get_settings()
    try:
        payload = jwt.decode(state, settings.jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="invalid_state") from exc
    if payload.get("purpose") != "fitbit_oauth_state":
        raise HTTPException(status_code=400, detail="invalid_state")
    if payload.get("sub") != str(user_id):
        raise HTTPException(status_code=400, detail="invalid_state")


def build_authorize(
    user: User, *, code_challenge: str, scopes: list[str] | None = None
) -> AuthorizePayload:
    """Return the URL the user should be sent to + a state token to send back."""
    state = _state_jwt(user.id)
    url = fitbit.authorize_url(
        state=state,
        code_challenge=code_challenge,
        scopes=scopes or DEFAULT_SCOPES,
    )
    return AuthorizePayload(authorize_url=url, state=state)


async def complete_callback(
    session: AsyncSession,
    user: User,
    *,
    code: str,
    state: str,
    code_verifier: str,
) -> FitbitConnection:
    _verify_state(state, user.id)
    tokens = await fitbit.exchange_code(code=code, code_verifier=code_verifier)

    access_enc = secretbox.encrypt(tokens.access_token)
    refresh_enc = secretbox.encrypt(tokens.refresh_token)

    stmt = (
        pg_insert(FitbitConnection)
        .values(
            user_id=user.id,
            fitbit_user_id=tokens.fitbit_user_id,
            access_token_encrypted=access_enc,
            refresh_token_encrypted=refresh_enc,
            expires_at=tokens.expires_at,
            scopes=tokens.scopes,
        )
        .on_conflict_do_update(
            index_elements=["user_id"],
            set_={
                "fitbit_user_id": tokens.fitbit_user_id,
                "access_token_encrypted": access_enc,
                "refresh_token_encrypted": refresh_enc,
                "expires_at": tokens.expires_at,
                "scopes": tokens.scopes,
                "updated_at": _now(),
            },
        )
    )
    await session.execute(stmt)
    await session.flush()
    record = (
        await session.execute(select(FitbitConnection).where(FitbitConnection.user_id == user.id))
    ).scalar_one()
    return record


async def disconnect(session: AsyncSession, user: User) -> bool:
    """Revoke with Fitbit (best-effort) and delete the connection row.
    Keeps imported activities + daily_metrics. Returns True if a row existed.
    """
    record = (
        await session.execute(select(FitbitConnection).where(FitbitConnection.user_id == user.id))
    ).scalar_one_or_none()
    if record is None:
        return False
    try:
        access_token = secretbox.decrypt(record.access_token_encrypted)
        await fitbit.revoke(access_token=access_token)
    except Exception:  # noqa: BLE001
        # Disconnect should always succeed locally even if Fitbit revoke fails.
        pass
    await session.delete(record)
    await session.flush()
    return True


async def get_connection(session: AsyncSession, user: User) -> FitbitConnection | None:
    return (
        await session.execute(select(FitbitConnection).where(FitbitConnection.user_id == user.id))
    ).scalar_one_or_none()
