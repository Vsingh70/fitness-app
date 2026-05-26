from typing import Any

import pytest
from httpx import AsyncClient

from app.services import auth as auth_service


async def _sign_in_apple(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    sub: str = "apple-test-sub",
    email: str | None = "apple@example.com",
) -> dict[str, Any]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=email)

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)

    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    assert response.status_code == 200, response.text
    return response.json()


async def test_apple_sign_in_then_me(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    pair = await _sign_in_apple(client, monkeypatch)
    assert pair["token_type"] == "Bearer"
    assert pair["expires_in"] > 0

    me_response = await client.get(
        "/v1/me", headers={"Authorization": f"Bearer {pair['access_token']}"}
    )
    assert me_response.status_code == 200
    me = me_response.json()
    assert me["email"] == "apple@example.com"
    assert me["unit_system"] == "imperial"
    assert me["timezone"] == "America/New_York"


async def test_me_requires_token(client: AsyncClient) -> None:
    response = await client.get("/v1/me")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"


async def test_me_rejects_bad_token(client: AsyncClient) -> None:
    response = await client.get(
        "/v1/me", headers={"Authorization": "Bearer not-a-real-jwt"}
    )
    assert response.status_code == 401


async def test_patch_me_updates_fields(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    pair = await _sign_in_apple(client, monkeypatch)
    headers = {"Authorization": f"Bearer {pair['access_token']}"}

    response = await client.patch(
        "/v1/me",
        headers=headers,
        json={"display_name": "Lifter", "unit_system": "metric", "timezone": "UTC"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "Lifter"
    assert body["unit_system"] == "metric"
    assert body["timezone"] == "UTC"


async def test_refresh_rotation_issues_new_pair(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    pair = await _sign_in_apple(client, monkeypatch)

    response = await client.post(
        "/v1/auth/refresh", json={"refresh_token": pair["refresh_token"]}
    )
    assert response.status_code == 200
    new_pair = response.json()
    assert new_pair["refresh_token"] != pair["refresh_token"]
    assert new_pair["access_token"] != pair["access_token"]


async def test_replay_of_revoked_refresh_revokes_chain(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_pair = await _sign_in_apple(client, monkeypatch)

    rotated = await client.post(
        "/v1/auth/refresh", json={"refresh_token": first_pair["refresh_token"]}
    )
    assert rotated.status_code == 200
    second_pair = rotated.json()

    # Replay the original refresh token: must 401 and revoke the chain.
    replay = await client.post(
        "/v1/auth/refresh", json={"refresh_token": first_pair["refresh_token"]}
    )
    assert replay.status_code == 401

    # The rotated refresh token should now also be revoked.
    follow_up = await client.post(
        "/v1/auth/refresh", json={"refresh_token": second_pair["refresh_token"]}
    )
    assert follow_up.status_code == 401


async def test_logout_revokes_refresh_tokens(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    pair = await _sign_in_apple(client, monkeypatch)
    headers = {"Authorization": f"Bearer {pair['access_token']}"}

    logout = await client.post("/v1/auth/logout", headers=headers)
    assert logout.status_code == 200

    after = await client.post(
        "/v1/auth/refresh", json={"refresh_token": pair["refresh_token"]}
    )
    assert after.status_code == 401


async def test_apple_sign_in_returns_503_when_unconfigured(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APPLE_BUNDLE_IDS", "")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        response = await client.post("/v1/auth/apple", json={"id_token": "anything"})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "integration_error"
    finally:
        monkeypatch.setenv(
            "APPLE_BUNDLE_IDS", "com.example.gym.ios,com.example.gym.web"
        )
        get_settings.cache_clear()


async def test_openapi_lists_auth_routes(client: AsyncClient) -> None:
    spec = (await client.get("/openapi.json")).json()
    paths = spec["paths"]
    for path in ("/v1/auth/apple", "/v1/auth/google", "/v1/auth/refresh", "/v1/auth/logout", "/v1/me"):
        assert path in paths, f"missing {path} in openapi paths"
