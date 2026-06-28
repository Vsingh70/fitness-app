from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.auth import LogoutResponse, RefreshRequest, SignInRequest, TokenPair
from app.services.auth import (
    VerifiedIdentity,
    issue_token_pair,
    revoke_active_tokens,
    rotate_refresh_token,
    upsert_apple_user,
    upsert_google_user,
    verify_apple_token,
    verify_google_token,
)
from app.services.rate_limit import check_auth_ip_limit


class DevSignInRequest(BaseModel):
    sub: str = Field(min_length=1, max_length=128)
    email: str | None = None


router = APIRouter(prefix="/auth", tags=["auth"])


def _strip_port(addr: str) -> str:
    """Strip a trailing port from an address. Caddy's X-Real-IP is ``{remote}`` =
    ``host:port``, but the INET audit column rejects a port and a per-IP rate-limit
    key must not include the ephemeral port. Handles IPv4 ``host:port``, bracketed
    IPv6 ``[::1]:port``, and bare addresses (returned unchanged)."""
    addr = addr.strip()
    if addr.startswith("["):  # [IPv6]:port
        return addr[1:].partition("]")[0]
    if addr.count(":") == 1:  # IPv4:port (bare IPv6 has multiple colons → left alone)
        return addr.rsplit(":", 1)[0]
    return addr


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ua = request.headers.get("user-agent")
    # Behind Caddy the socket peer is always 127.0.0.1; Caddy sets X-Real-IP to the
    # true client and overwrites any client-supplied value, so it's trustworthy (the
    # app only binds localhost, so this header can't be spoofed end-to-end). Fall back
    # to the socket peer for local/dev where there's no proxy.
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        ip: str | None = _strip_port(real_ip)
    else:
        ip = request.client.host if request.client else None
    return ua, ip


async def _rate_limit(ip: str | None) -> None:
    """Per-IP cap (30/min) on the unauthenticated auth endpoints. Fails open if
    Redis is unavailable; a no-op when the client IP is unknown."""
    if ip:
        await check_auth_ip_limit(ip)


@router.post("/apple", response_model=TokenPair)
async def sign_in_with_apple(
    body: SignInRequest,
    request: Request,
    session: AsyncSession = Depends(db_session),
) -> TokenPair:
    ua, ip = _client_meta(request)
    await _rate_limit(ip)
    identity = await verify_apple_token(body.id_token)
    user = await upsert_apple_user(session, identity)
    pair = await issue_token_pair(session, user, user_agent=ua, ip=ip)
    await session.commit()
    return pair


@router.post("/google", response_model=TokenPair)
async def sign_in_with_google(
    body: SignInRequest,
    request: Request,
    session: AsyncSession = Depends(db_session),
) -> TokenPair:
    ua, ip = _client_meta(request)
    await _rate_limit(ip)
    identity = verify_google_token(body.id_token)
    user = await upsert_google_user(session, identity)
    pair = await issue_token_pair(session, user, user_agent=ua, ip=ip)
    await session.commit()
    return pair


@router.post("/refresh", response_model=TokenPair)
async def refresh_session(
    body: RefreshRequest,
    request: Request,
    session: AsyncSession = Depends(db_session),
) -> TokenPair:
    ua, ip = _client_meta(request)
    await _rate_limit(ip)
    pair = await rotate_refresh_token(session, body.refresh_token, user_agent=ua, ip=ip)
    await session.commit()
    return pair


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> LogoutResponse:
    await revoke_active_tokens(session, current_user.id)
    await session.commit()
    return LogoutResponse()


@router.post("/dev", response_model=TokenPair, include_in_schema=False)
async def dev_sign_in(
    body: DevSignInRequest,
    request: Request,
    session: AsyncSession = Depends(db_session),
) -> TokenPair:
    """Dev-only sign-in used by Playwright. Disabled when ENVIRONMENT=prod."""
    if get_settings().environment == "prod":
        raise HTTPException(status_code=404, detail="Not found.")
    ua, ip = _client_meta(request)
    await _rate_limit(ip)
    identity = VerifiedIdentity(sub=body.sub, email=body.email)
    user = await upsert_apple_user(session, identity)
    pair = await issue_token_pair(session, user, user_agent=ua, ip=ip)
    await session.commit()
    return pair
