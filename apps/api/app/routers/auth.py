from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.auth import LogoutResponse, RefreshRequest, SignInRequest, TokenPair
from app.services.auth import (
    issue_token_pair,
    revoke_active_tokens,
    rotate_refresh_token,
    upsert_apple_user,
    upsert_google_user,
    verify_apple_token,
    verify_google_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    return ua, ip


@router.post("/apple", response_model=TokenPair)
async def sign_in_with_apple(
    body: SignInRequest,
    request: Request,
    session: AsyncSession = Depends(db_session),
) -> TokenPair:
    identity = await verify_apple_token(body.id_token)
    user = await upsert_apple_user(session, identity)
    ua, ip = _client_meta(request)
    pair = await issue_token_pair(session, user, user_agent=ua, ip=ip)
    await session.commit()
    return pair


@router.post("/google", response_model=TokenPair)
async def sign_in_with_google(
    body: SignInRequest,
    request: Request,
    session: AsyncSession = Depends(db_session),
) -> TokenPair:
    identity = verify_google_token(body.id_token)
    user = await upsert_google_user(session, identity)
    ua, ip = _client_meta(request)
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
