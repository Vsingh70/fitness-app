"""Google Health OAuth (Phase 1 spike) tests with httpx mocked.

Covers:
- authorize URL building (scopes + PKCE + offline/consent params)
- token-exchange + refresh response parsing (mocked httpx)
- id_token -> google_user_id extraction
- authorize/callback HTTP round-trip stores an encrypted connection row
- bad-state rejection
- status endpoint reflects connection state

The probe is intentionally lightly tested (it's a spike tool that hits the
real Google API to discover shapes); we only assert it 400s when not connected.
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.clients import google_health as gh_client
from app.db import get_sessionmaker
from app.models.fitbit_connection import FitbitConnection
from app.services import auth as auth_service
from app.services.security import secretbox


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "gh-sub"
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _id_token_with_sub(sub: str) -> str:
    """Build an unsigned JWT-shaped string with the given sub claim."""

    def b64(obj: dict[str, Any]) -> str:
        raw = json.dumps(obj).encode("ascii")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    return f"{b64({'alg': 'RS256'})}.{b64({'sub': sub, 'email': 'x@y.z'})}.sig"


# ---------------------------------------------------------------------------
# authorize URL building (pure)
# ---------------------------------------------------------------------------


def test_build_authorize_url_has_scopes_and_pkce_params() -> None:
    url = gh_client.build_authorize_url(
        state="state-123",
        code_challenge="challenge-abc",
        scopes=gh_client.DEFAULT_SCOPES,
    )
    parsed = urlparse(url)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == gh_client.AUTHORIZE_URL

    q = parse_qs(parsed.query)
    assert q["response_type"] == ["code"]
    assert q["code_challenge"] == ["challenge-abc"]
    assert q["code_challenge_method"] == ["S256"]
    assert q["access_type"] == ["offline"]
    assert q["prompt"] == ["consent"]
    assert q["state"] == ["state-123"]
    assert q["client_id"] == ["test-google-health-client"]
    assert q["redirect_uri"] == ["https://178-156-183-7.sslip.io/integrations/health/callback"]

    scope = q["scope"][0]
    assert "https://www.googleapis.com/auth/" in scope
    assert "googlehealth.health_metrics_and_measurements.readonly" in scope
    assert "googlehealth.activity_and_fitness.readonly" in scope
    assert "googlehealth.sleep.readonly" in scope
    assert "openid" in scope


# ---------------------------------------------------------------------------
# token exchange / refresh parsing (mocked httpx)
# ---------------------------------------------------------------------------


def _mock_token_response(monkeypatch: pytest.MonkeyPatch, body: dict[str, Any]) -> list[dict]:
    """Patch httpx.AsyncClient.post used by the token endpoint. Returns a list
    that captures the form data sent, for assertions.
    """
    captured: list[dict] = []

    class _Resp:
        status_code = 200

        def __init__(self, payload: dict[str, Any]) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return self._payload

        @property
        def text(self) -> str:
            return json.dumps(self._payload)

    class _FakeClient:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        async def __aenter__(self) -> _FakeClient:
            return self

        async def __aexit__(self, *a: Any) -> None:
            return None

        async def post(self, url: str, data: dict, headers: dict) -> _Resp:
            captured.append({"url": url, "data": data})
            return _Resp(body)

    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)
    return captured


async def test_exchange_code_parses_tokens_and_sub(monkeypatch: pytest.MonkeyPatch) -> None:
    body = {
        "access_token": "ya29.access",
        "refresh_token": "1//refresh",
        "expires_in": 3599,
        "scope": " ".join(gh_client.DEFAULT_SCOPES),
        "token_type": "Bearer",
        "id_token": _id_token_with_sub("google-user-xyz"),
    }
    captured = _mock_token_response(monkeypatch, body)

    tokens = await gh_client.exchange_code(code="auth-code", code_verifier="verifier-1234567890")

    assert tokens.access_token == "ya29.access"
    assert tokens.refresh_token == "1//refresh"
    assert tokens.google_user_id == "google-user-xyz"
    assert tokens.expires_at > datetime.now(tz=UTC) + timedelta(minutes=50)
    assert "openid" in tokens.scopes

    # The token request hit Google's token endpoint with the right grant + creds.
    sent = captured[-1]
    assert sent["url"] == gh_client.TOKEN_URL
    assert sent["data"]["grant_type"] == "authorization_code"
    assert sent["data"]["code"] == "auth-code"
    assert sent["data"]["code_verifier"] == "verifier-1234567890"
    assert sent["data"]["client_id"] == "test-google-health-client"
    assert sent["data"]["client_secret"] == "test-google-health-secret"


async def test_refresh_keeps_existing_refresh_token_when_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Google typically omits refresh_token on refresh; we keep the old one.
    body = {
        "access_token": "ya29.access2",
        "expires_in": 3599,
        "scope": " ".join(gh_client.DEFAULT_SCOPES),
        "token_type": "Bearer",
    }
    _mock_token_response(monkeypatch, body)

    tokens = await gh_client.refresh_tokens(refresh_token="1//original-refresh")
    assert tokens.access_token == "ya29.access2"
    assert tokens.refresh_token == "1//original-refresh"


# ---------------------------------------------------------------------------
# OAuth HTTP round-trip
# ---------------------------------------------------------------------------


async def test_authorize_and_callback_creates_connection_row(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)

    auth = (
        await client.post(
            "/v1/integrations/health/authorize",
            headers=headers,
            json={"code_challenge": "challenge-" + "x" * 32},
        )
    ).json()
    assert auth["authorize_url"].startswith(gh_client.AUTHORIZE_URL)
    assert auth["state"]

    tokens = gh_client.GoogleHealthTokens(
        access_token="ya29.access",
        refresh_token="1//refresh",
        expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
        scopes=gh_client.DEFAULT_SCOPES,
        google_user_id="google-user-xyz",
    )

    async def fake_exchange(**kw: Any) -> gh_client.GoogleHealthTokens:
        return tokens

    monkeypatch.setattr(gh_client, "exchange_code", fake_exchange)

    callback = await client.post(
        "/v1/integrations/health/callback",
        headers=headers,
        json={
            "code": "auth-code",
            "state": auth["state"],
            "code_verifier": "verifier-" + "y" * 40,
        },
    )
    assert callback.status_code == 200, callback.text
    assert callback.json()["connected"] is True
    assert "openid" in callback.json()["scopes"]

    sm = get_sessionmaker()
    async with sm() as db:
        rows = (await db.execute(select(FitbitConnection))).scalars().all()
    assert len(rows) == 1
    assert rows[0].fitbit_user_id == "google-user-xyz"
    # Tokens are encrypted at rest.
    assert rows[0].access_token_encrypted != tokens.access_token
    assert secretbox.decrypt(rows[0].access_token_encrypted) == tokens.access_token
    assert secretbox.decrypt(rows[0].refresh_token_encrypted) == tokens.refresh_token


async def test_callback_rejects_bad_state(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    response = await client.post(
        "/v1/integrations/health/callback",
        headers=headers,
        json={
            "code": "auth-code",
            "state": "not-a-real-jwt",
            "code_verifier": "verifier-" + "y" * 40,
        },
    )
    assert response.status_code == 400


async def test_status_reflects_connection_and_probe_requires_connection(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)

    before = (await client.get("/v1/integrations/health/status", headers=headers)).json()
    assert before["connected"] is False

    # Probe before connecting -> 400.
    probe_unconnected = await client.post("/v1/integrations/health/probe", headers=headers)
    assert probe_unconnected.status_code == 400

    # Connect.
    auth = (
        await client.post(
            "/v1/integrations/health/authorize",
            headers=headers,
            json={"code_challenge": "challenge-" + "x" * 32},
        )
    ).json()
    tokens = gh_client.GoogleHealthTokens(
        access_token="ya29.access",
        refresh_token="1//refresh",
        expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
        scopes=gh_client.DEFAULT_SCOPES,
        google_user_id="google-user-xyz",
    )

    async def fake_exchange(**kw: Any) -> gh_client.GoogleHealthTokens:
        return tokens

    monkeypatch.setattr(gh_client, "exchange_code", fake_exchange)
    await client.post(
        "/v1/integrations/health/callback",
        headers=headers,
        json={
            "code": "auth-code",
            "state": auth["state"],
            "code_verifier": "verifier-" + "y" * 40,
        },
    )

    after = (await client.get("/v1/integrations/health/status", headers=headers)).json()
    assert after["connected"] is True

    # Probe after connecting calls the client with the decrypted token.
    seen_tokens: list[str] = []

    async def fake_probe(*, access_token: str) -> list[gh_client.ProbeResult]:
        seen_tokens.append(access_token)
        return [
            gh_client.ProbeResult(
                label="weight_dataPoints_v4",
                method="GET",
                url="https://health.googleapis.com/v4/users/me/dataTypes/com.google.weight/dataPoints",
                status=200,
                ok=True,
                body_snippet={"dataPoints": []},
            )
        ]

    monkeypatch.setattr(gh_client, "probe_data", fake_probe)
    probe = await client.post("/v1/integrations/health/probe", headers=headers)
    assert probe.status_code == 200, probe.text
    assert seen_tokens == ["ya29.access"]
    assert probe.json()["results"][0]["label"] == "weight_dataPoints_v4"
