"""Account deletion: DELETE /v1/me (soft-delete + 7-day grace).

Covers the request side of the feature: DELETE /me stamps deleted_at, revokes
refresh tokens, and returns 204; the still-valid access token is then rejected
on authed endpoints; and re-authenticating as a deleted user is refused (the
account is permanent, not restored). The nightly purge itself lives in
test_soft_delete_gc.py.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.db import get_sessionmaker
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services import auth as auth_service


async def _sign_in(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    sub: str = "delete-sub",
    email: str | None = "delete@example.com",
) -> dict[str, Any]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=email)

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    assert response.status_code == 200, response.text
    return response.json()


async def test_delete_me_marks_deleted_revokes_tokens_and_returns_204(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    pair = await _sign_in(client, monkeypatch)
    headers = {"Authorization": f"Bearer {pair['access_token']}"}

    response = await client.delete("/v1/me", headers=headers)
    assert response.status_code == 204
    assert response.content == b""

    sm = get_sessionmaker()
    async with sm() as session:
        user = (
            await session.execute(select(User).where(User.apple_sub == "delete-sub"))
        ).scalar_one()
        assert user.deleted_at is not None

        # Every refresh token for the user is revoked.
        active = (
            await session.execute(
                select(func.count())
                .select_from(RefreshToken)
                .where(
                    RefreshToken.user_id == user.id,
                    RefreshToken.revoked_at.is_(None),
                )
            )
        ).scalar()
        assert active == 0

    # The revoked refresh token can no longer rotate.
    refresh = await client.post("/v1/auth/refresh", json={"refresh_token": pair["refresh_token"]})
    assert refresh.status_code == 401


async def test_delete_me_is_idempotent(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    pair = await _sign_in(client, monkeypatch)
    headers = {"Authorization": f"Bearer {pair['access_token']}"}

    first = await client.delete("/v1/me", headers=headers)
    assert first.status_code == 204

    sm = get_sessionmaker()
    async with sm() as session:
        user = (
            await session.execute(select(User).where(User.apple_sub == "delete-sub"))
        ).scalar_one()
        first_deleted_at = user.deleted_at
        assert first_deleted_at is not None

    # The access token is now rejected, so a second DELETE with the same token 401s
    # rather than re-stamping deleted_at.
    second = await client.delete("/v1/me", headers=headers)
    assert second.status_code == 401

    async with sm() as session:
        user = (
            await session.execute(select(User).where(User.apple_sub == "delete-sub"))
        ).scalar_one()
        assert user.deleted_at == first_deleted_at


async def test_deleted_user_access_token_is_rejected(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    pair = await _sign_in(client, monkeypatch)
    headers = {"Authorization": f"Bearer {pair['access_token']}"}

    # The access token is valid up until the account is marked for deletion.
    assert (await client.get("/v1/me", headers=headers)).status_code == 200

    delete = await client.delete("/v1/me", headers=headers)
    assert delete.status_code == 204

    # Same (still-unexpired) access token is now rejected: the user is logged out.
    after = await client.get("/v1/me", headers=headers)
    assert after.status_code == 401
    assert after.json()["error"]["code"] == "unauthorized"


async def test_sign_in_as_deleted_user_is_rejected(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    pair = await _sign_in(client, monkeypatch, sub="deleted-then-back")
    headers = {"Authorization": f"Bearer {pair['access_token']}"}
    assert (await client.delete("/v1/me", headers=headers)).status_code == 204

    # Re-authenticating with the same OAuth subject must NOT restore the account.
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub="deleted-then-back", email="x@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    assert response.status_code == 403
    assert response.json()["error"]["message"] == "Account is scheduled for deletion."


async def test_fresh_sub_still_creates_account_after_a_deletion(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # One user deletes their account...
    pair = await _sign_in(client, monkeypatch, sub="gone")
    assert (
        await client.delete("/v1/me", headers={"Authorization": f"Bearer {pair['access_token']}"})
    ).status_code == 204

    # ...a different, never-seen sub signs in normally and gets a working session.
    fresh = await _sign_in(client, monkeypatch, sub="brand-new", email="new@example.com")
    me = await client.get("/v1/me", headers={"Authorization": f"Bearer {fresh['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "new@example.com"


async def test_delete_me_requires_auth(client: AsyncClient) -> None:
    response = await client.delete("/v1/me")
    assert response.status_code == 401
