"""Account deletion: DELETE /v1/me (soft-delete + 7-day grace).

Covers the request side of the feature: DELETE /me stamps deleted_at, detaches
the identity (email/apple_sub/google_sub), revokes refresh tokens, and returns
204; the still-valid access token is then rejected on authed endpoints; and
re-authenticating with the same OAuth subject starts a brand-new empty account
("start fresh") rather than restoring the deleted one. The nightly purge itself
lives in test_soft_delete_gc.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
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


async def test_delete_me_marks_deleted_detaches_identity_and_revokes_tokens(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    pair = await _sign_in(client, monkeypatch)
    headers = {"Authorization": f"Bearer {pair['access_token']}"}

    sm = get_sessionmaker()
    async with sm() as session:
        # Deletion detaches apple_sub, so capture the row by id while it's intact.
        user_id = (
            await session.execute(select(User.id).where(User.apple_sub == "delete-sub"))
        ).scalar_one()

    response = await client.delete("/v1/me", headers=headers)
    assert response.status_code == 204
    assert response.content == b""

    async with sm() as session:
        user = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
        assert user.deleted_at is not None
        # Identity is detached so the user can immediately start a fresh account.
        assert user.email is None
        assert user.apple_sub is None
        assert user.google_sub is None

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

    sm = get_sessionmaker()
    async with sm() as session:
        # Deletion detaches apple_sub, so capture the row by id while it's intact.
        user_id = (
            await session.execute(select(User.id).where(User.apple_sub == "delete-sub"))
        ).scalar_one()

    first = await client.delete("/v1/me", headers=headers)
    assert first.status_code == 204

    async with sm() as session:
        user = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
        first_deleted_at = user.deleted_at
        assert first_deleted_at is not None

    # The access token is now rejected, so a second DELETE with the same token 401s
    # rather than re-stamping deleted_at.
    second = await client.delete("/v1/me", headers=headers)
    assert second.status_code == 401

    async with sm() as session:
        user = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
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


async def test_sign_in_after_deletion_starts_fresh_account(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    pair = await _sign_in(client, monkeypatch, sub="deleted-then-back")
    headers = {"Authorization": f"Bearer {pair['access_token']}"}

    sm = get_sessionmaker()
    async with sm() as session:
        old_id = (
            await session.execute(select(User.id).where(User.apple_sub == "deleted-then-back"))
        ).scalar_one()

    assert (await client.delete("/v1/me", headers=headers)).status_code == 204

    # Re-authenticating with the same OAuth subject creates a brand-new account
    # rather than restoring (or rejecting) the deleted one.
    fresh = await _sign_in(client, monkeypatch, sub="deleted-then-back", email="back@example.com")
    me = await client.get("/v1/me", headers={"Authorization": f"Bearer {fresh['access_token']}"})
    assert me.status_code == 200

    async with sm() as session:
        # A new row now owns the sub; the old (deleted) row was detached and remains.
        new_id = (
            await session.execute(select(User.id).where(User.apple_sub == "deleted-then-back"))
        ).scalar_one()
        assert new_id != old_id

        old = (await session.execute(select(User).where(User.id == old_id))).scalar_one()
        assert old.deleted_at is not None
        assert old.apple_sub is None


async def test_fresh_account_after_deletion_carries_no_old_profile(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    pair = await _sign_in(client, monkeypatch, sub="recycle", email="recycle@example.com")
    headers = {"Authorization": f"Bearer {pair['access_token']}"}

    # Personalize the original account, then delete it.
    patched = await client.patch("/v1/me", json={"display_name": "Original"}, headers=headers)
    assert patched.status_code == 200
    assert patched.json()["display_name"] == "Original"
    assert (await client.delete("/v1/me", headers=headers)).status_code == 204

    # Signing back in with the same sub yields a clean account: none of the old
    # profile carries over.
    fresh = await _sign_in(client, monkeypatch, sub="recycle", email="recycle@example.com")
    me = await client.get("/v1/me", headers={"Authorization": f"Bearer {fresh['access_token']}"})
    assert me.status_code == 200
    assert me.json()["display_name"] is None


async def test_sign_in_self_heals_a_deleted_row_that_kept_its_identity(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Simulate a row deleted by older code: deleted_at is set but the identity was
    # never detached (the invariant the upsert now defends against). Re-signing-in
    # must not 500 or sign into the deleted row — it detaches and starts fresh.
    await _sign_in(client, monkeypatch, sub="legacy-deleted", email="legacy@example.com")
    sm = get_sessionmaker()
    async with sm() as session:
        stuck = (
            await session.execute(select(User).where(User.apple_sub == "legacy-deleted"))
        ).scalar_one()
        old_id = stuck.id
        stuck.deleted_at = datetime.now(tz=UTC)
        await session.commit()

    fresh = await _sign_in(client, monkeypatch, sub="legacy-deleted", email="legacy@example.com")
    me = await client.get("/v1/me", headers={"Authorization": f"Bearer {fresh['access_token']}"})
    assert me.status_code == 200

    async with sm() as session:
        new_id = (
            await session.execute(
                select(User.id).where(User.apple_sub == "legacy-deleted", User.deleted_at.is_(None))
            )
        ).scalar_one()
        assert new_id != old_id
        old = (await session.execute(select(User).where(User.id == old_id))).scalar_one()
        assert old.deleted_at is not None
        assert old.apple_sub is None  # detached on the way to creating the fresh account


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
