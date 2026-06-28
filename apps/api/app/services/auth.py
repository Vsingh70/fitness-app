import asyncio
import hashlib
import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.logging_config import get_logger
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import TokenPair

log = get_logger("auth")

APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"

# Apple's signing keys rotate rarely; the auth contract (tasks/01-foundation/03-auth.md)
# specifies caching the JWKS for one hour.
_apple_jwks_cache: dict[str, Any] = {"fetched_at": 0.0, "keys": None}
APPLE_JWKS_TTL_SECONDS = 3600

# Single-flight lock so a cache miss/expiry triggers exactly one concurrent refresh
# (guards against a thundering herd of outbound JWKS fetches).
_apple_jwks_lock = asyncio.Lock()


@dataclass(frozen=True)
class VerifiedIdentity:
    sub: str
    email: str | None


def _hash_refresh(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _require_audiences(audiences: list[str], provider: str) -> list[str]:
    if not audiences:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{provider} sign-in is not configured.",
        )
    return audiences


async def _fetch_apple_jwks_remote(
    http_client: httpx.AsyncClient | None = None,
) -> list[dict[str, Any]]:
    owned_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=5.0)
    try:
        response = await client.get(APPLE_JWKS_URL)
        response.raise_for_status()
        return response.json()["keys"]  # type: ignore[no-any-return]
    finally:
        if owned_client:
            await client.aclose()


async def _fetch_apple_jwks(http_client: httpx.AsyncClient | None = None) -> list[dict[str, Any]]:
    now = time.monotonic()
    cached = _apple_jwks_cache.get("keys")
    if cached is not None and now - _apple_jwks_cache["fetched_at"] < APPLE_JWKS_TTL_SECONDS:
        return cached  # type: ignore[no-any-return]

    # Single-flight: only one coroutine refreshes at a time. Others wait, then re-check
    # the cache (the winner will have populated it) instead of stampeding Apple.
    async with _apple_jwks_lock:
        now = time.monotonic()
        cached = _apple_jwks_cache.get("keys")
        if cached is not None and now - _apple_jwks_cache["fetched_at"] < APPLE_JWKS_TTL_SECONDS:
            return cached  # type: ignore[no-any-return]

        try:
            keys = await _fetch_apple_jwks_remote(http_client)
        except Exception as exc:
            # Stale-while-revalidate: if the refresh fails but we still hold a previously
            # fetched keyset, keep serving it rather than failing all sign-ins. Apple's
            # keys are long-lived, so a slightly stale set is far safer than an outage.
            if cached is not None:
                log.warning(
                    "apple_jwks_refresh_failed_serving_stale",
                    error=str(exc),
                    stale_age_seconds=round(now - _apple_jwks_cache["fetched_at"], 1),
                )
                return cached  # type: ignore[no-any-return]
            raise

        _apple_jwks_cache["keys"] = keys
        _apple_jwks_cache["fetched_at"] = time.monotonic()
        return keys


def _reset_apple_jwks_cache_for_tests() -> None:
    _apple_jwks_cache["keys"] = None
    _apple_jwks_cache["fetched_at"] = 0.0


async def verify_apple_token(
    id_token_str: str,
    *,
    jwks_override: list[dict[str, Any]] | None = None,
) -> VerifiedIdentity:
    audiences = _require_audiences(get_settings().apple_bundle_ids, "Apple")

    keys = jwks_override if jwks_override is not None else await _fetch_apple_jwks()
    try:
        unverified_header = jwt.get_unverified_header(id_token_str)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Malformed Apple token.") from exc

    matching_key = next(
        (key for key in keys if key.get("kid") == unverified_header.get("kid")),
        None,
    )
    if matching_key is None:
        raise HTTPException(status_code=401, detail="Apple token signing key not found.")

    last_error: Exception | None = None
    claims = None
    for audience in audiences:
        try:
            claims = jwt.decode(
                id_token_str,
                matching_key,
                algorithms=[matching_key.get("alg", "RS256")],
                audience=audience,
                issuer=APPLE_ISSUER,
            )
            break
        except Exception as exc:
            last_error = exc
    if claims is None:
        raise HTTPException(status_code=401, detail="Invalid Apple token.") from last_error

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Apple token missing subject.")
    email = claims.get("email")
    return VerifiedIdentity(sub=str(sub), email=email)


def verify_google_token(id_token_str: str) -> VerifiedIdentity:
    audiences = _require_audiences(get_settings().google_client_ids, "Google")

    try:
        claims = google_id_token.verify_oauth2_token(  # type: ignore[no-untyped-call]
            id_token_str, google_requests.Request()
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid Google token.") from exc

    if claims.get("aud") not in audiences:
        raise HTTPException(status_code=401, detail="Google token audience mismatch.")

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Google token missing subject.")
    email = claims.get("email")
    return VerifiedIdentity(sub=str(sub), email=email)


def _detach_identity(user: User) -> None:
    """Free a user's unique identity keys (email + Apple/Google subs).

    Called on account deletion so the soft-deleted row stops occupying the unique
    keys: the user can sign in again and get a brand-new account ("start fresh").
    """
    user.email = None
    user.apple_sub = None
    user.google_sub = None


async def upsert_apple_user(session: AsyncSession, identity: VerifiedIdentity) -> User:
    user = (
        await session.execute(select(User).where(User.apple_sub == identity.sub))
    ).scalar_one_or_none()
    if user is not None:
        if user.deleted_at is None:
            return user
        # Defensive: a soft-deleted row that still holds its identity (e.g. an
        # account deleted by older code during a deploy, before detach existed).
        # Detach it so the unique keys are free, then fall through to create a
        # fresh account — never sign the user into a deleted account.
        _detach_identity(user)
        await session.flush()

    user = User(apple_sub=identity.sub, email=identity.email)
    session.add(user)
    await session.flush()
    return user


async def upsert_google_user(session: AsyncSession, identity: VerifiedIdentity) -> User:
    user = (
        await session.execute(select(User).where(User.google_sub == identity.sub))
    ).scalar_one_or_none()
    if user is not None:
        if user.deleted_at is None:
            if identity.email and not user.email:
                user.email = identity.email
            return user
        # Defensive: detach a not-yet-detached soft-deleted row, then start fresh.
        _detach_identity(user)
        await session.flush()

    user = User(google_sub=identity.sub, email=identity.email)
    session.add(user)
    await session.flush()
    return user


def _issue_access_token(user_id: UUID) -> tuple[str, int]:
    settings = get_settings()
    ttl_seconds = settings.jwt_access_ttl_minutes * 60
    issued = int(_now().timestamp())
    payload = {
        "sub": str(user_id),
        "iat": issued,
        "exp": issued + ttl_seconds,
        "jti": secrets.token_urlsafe(16),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return token, ttl_seconds


async def issue_token_pair(
    session: AsyncSession,
    user: User,
    *,
    user_agent: str | None = None,
    ip: str | None = None,
) -> TokenPair:
    access_token, ttl_seconds = _issue_access_token(user.id)

    raw_refresh = secrets.token_urlsafe(32)
    expires_at = _now() + timedelta(days=get_settings().refresh_ttl_days)
    refresh = RefreshToken(
        user_id=user.id,
        token_hash=_hash_refresh(raw_refresh),
        expires_at=expires_at,
        user_agent=user_agent,
        ip=ip,
    )
    session.add(refresh)
    await session.flush()

    return TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=ttl_seconds,
    )


async def _revoke_chain(session: AsyncSession, head: RefreshToken) -> None:
    """Walk forward through rotated_to and mark every token in the chain revoked."""
    now = _now()
    current: RefreshToken | None = head
    visited: set[UUID] = set()
    while current is not None and current.id not in visited:
        visited.add(current.id)
        if current.revoked_at is None:
            current.revoked_at = now
        if current.rotated_to is None:
            break
        current = (
            await session.execute(select(RefreshToken).where(RefreshToken.id == current.rotated_to))
        ).scalar_one_or_none()


async def rotate_refresh_token(
    session: AsyncSession,
    raw_refresh: str,
    *,
    user_agent: str | None = None,
    ip: str | None = None,
) -> TokenPair:
    token_hash = _hash_refresh(raw_refresh)
    existing = (
        await session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    ).scalar_one_or_none()

    if existing is None:
        raise HTTPException(status_code=401, detail="Refresh token not recognized.")

    now = _now()

    if existing.revoked_at is not None:
        # A token that was *just* rotated and whose child is still live is almost
        # certainly a benign concurrent/duplicate refresh from the same client — e.g.
        # a cold browser tab firing several queries at once, each refreshing the same
        # token before any of them sees the rotation. Tolerating it inside a short
        # grace window stops a legitimate burst from nuking the whole session; outside
        # the window (or once the chain has moved on) it is treated as a genuine replay.
        grace = timedelta(seconds=get_settings().refresh_rotation_grace_seconds)
        child = (
            (
                await session.execute(
                    select(RefreshToken).where(RefreshToken.id == existing.rotated_to)
                )
            ).scalar_one_or_none()
            if existing.rotated_to is not None
            else None
        )
        child_live = child is not None and child.revoked_at is None and child.expires_at > now
        if now - existing.revoked_at <= grace and child_live:
            user = (
                await session.execute(select(User).where(User.id == existing.user_id))
            ).scalar_one_or_none()
            if user is not None:
                # Grace tolerates the reuse instead of revoking, which silences the
                # replay tripwire for this window — log it so a concurrent reuse from a
                # different client (possible token theft) is still observable.
                log.info(
                    "refresh_rotation_grace_applied",
                    user_id=str(existing.user_id),
                    ip=ip,
                    user_agent=user_agent,
                )
                return await issue_token_pair(session, user, user_agent=user_agent, ip=ip)

        # Replay detected: revoke the entire chain plus any siblings still active.
        # In a no-RLS app this is the primary token-theft signal, so emit a warning.
        log.warning(
            "refresh_token_replay_detected",
            user_id=str(existing.user_id),
            ip=ip,
            user_agent=user_agent,
        )
        await _revoke_chain(session, existing)
        siblings = (
            (
                await session.execute(
                    select(RefreshToken).where(
                        RefreshToken.user_id == existing.user_id,
                        RefreshToken.revoked_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        for sibling in siblings:
            sibling.revoked_at = now
        await session.commit()
        raise HTTPException(status_code=401, detail="Refresh token replay detected.")

    if existing.expires_at <= now:
        existing.revoked_at = now
        await session.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired.")

    user = (
        await session.execute(select(User).where(User.id == existing.user_id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists.")

    new_pair = await issue_token_pair(session, user, user_agent=user_agent, ip=ip)

    new_record = (
        await session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == _hash_refresh(new_pair.refresh_token)
            )
        )
    ).scalar_one()

    existing.revoked_at = now
    existing.rotated_to = new_record.id
    await session.flush()
    return new_pair


async def revoke_active_tokens(session: AsyncSession, user_id: UUID) -> None:
    """Logout: revoke every non-revoked refresh token for the user."""
    now = _now()
    active = (
        (
            await session.execute(
                select(RefreshToken).where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    for token in active:
        token.revoked_at = now
    await session.flush()


async def soft_delete_account(session: AsyncSession, user: User) -> None:
    """Mark the user's account for deletion and log them out everywhere.

    Idempotent: stamps ``deleted_at`` only if not already set, then revokes all
    of the user's non-revoked refresh tokens so the session ends immediately.
    The account is hard-purged after the 7-day grace window by the nightly
    ``purge_deleted_users`` job. The caller commits the session.

    On deletion we also detach the identity (email + OAuth subs) from the row so
    the unique keys are freed immediately: signing in again with the same Apple/
    Google account creates a brand-new empty account ("start fresh"). The
    soft-deleted row keeps its owned data until the grace window elapses.
    """
    if user.deleted_at is None:
        user.deleted_at = _now()
        _detach_identity(user)
    await revoke_active_tokens(session, user.id)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except Exception as current_exc:
        # Rotation grace period: a token may have been signed with the previous secret
        # right before a rotation. Retry against it (if configured) so in-flight tokens
        # are not abruptly invalidated.
        previous_secret = settings.jwt_secret_previous
        if previous_secret:
            try:
                claims = jwt.decode(token, previous_secret, algorithms=["HS256"])
            except Exception:
                raise HTTPException(
                    status_code=401, detail="Invalid access token."
                ) from current_exc
            log.warning(
                "access_token_verified_with_previous_secret",
                jti=claims.get("jti"),
                sub=claims.get("sub"),
            )
            return claims
        raise HTTPException(status_code=401, detail="Invalid access token.") from current_exc
