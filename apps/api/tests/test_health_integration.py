"""Google Health OAuth + sync tests with httpx mocked.

Covers:
- authorize URL building (scopes + PKCE + offline/consent params)
- token-exchange + refresh response parsing (mocked httpx)
- id_token -> google_user_id extraction
- authorize/callback HTTP round-trip stores an encrypted connection row
- bad-state rejection
- status endpoint reflects connection state
- sync writes measurements into body_metrics (idempotently) + disconnect
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, date, datetime, timedelta
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


async def test_status_sync_and_disconnect_round_trip(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from decimal import Decimal

    from app.models.body_metric import BodyMetric

    headers = await _sign_in(client, monkeypatch)

    before = (await client.get("/v1/integrations/health/status", headers=headers)).json()
    assert before["connected"] is False

    # Sync before connecting writes nothing (no connection row).
    sync_unconnected = await client.post("/v1/integrations/health/sync", headers=headers)
    assert sync_unconnected.status_code == 200
    assert sync_unconnected.json() == {
        "weight_written": 0,
        "body_fat_written": 0,
        "daily_metrics_written": 0,
    }

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

    # Sync after connecting calls the client with the decrypted token and writes
    # the returned measurements into body_metrics.
    seen_tokens: list[str] = []
    recorded_at = datetime(2026, 4, 2, 13, 35, 13, tzinfo=UTC)

    async def fake_list_weight(
        *, access_token: str, since: Any = None
    ) -> list[gh_client.HealthMeasurement]:
        seen_tokens.append(access_token)
        return [gh_client.HealthMeasurement(recorded_at=recorded_at, weight_kg=Decimal("76.66"))]

    async def fake_list_body_fat(
        *, access_token: str, since: Any = None
    ) -> list[gh_client.HealthMeasurement]:
        return []

    monkeypatch.setattr(gh_client, "list_weight", fake_list_weight)
    monkeypatch.setattr(gh_client, "list_body_fat", fake_list_body_fat)

    # Daily-metric readers: one steps row exercises the daily_metrics upsert; the
    # rest return empty so the merge still produces a single dated row.
    metric_day = date(2026, 4, 2)

    async def fake_list_steps(
        *, access_token: str, since: Any = None
    ) -> list[gh_client.DailySummary]:
        return [gh_client.DailySummary(date=metric_day, steps=8000)]

    async def fake_list_heart_rate(
        *, access_token: str, since: Any = None
    ) -> list[gh_client.DailySummary]:
        return []

    async def fake_list_hrv(
        *, access_token: str, since: Any = None
    ) -> list[gh_client.DailySummary]:
        return []

    async def fake_list_sleep(
        *, access_token: str, since: Any = None
    ) -> list[gh_client.DailySummary]:
        return []

    monkeypatch.setattr(gh_client, "list_steps", fake_list_steps)
    monkeypatch.setattr(gh_client, "list_heart_rate", fake_list_heart_rate)
    monkeypatch.setattr(gh_client, "list_hrv", fake_list_hrv)
    monkeypatch.setattr(gh_client, "list_sleep", fake_list_sleep)

    sync = await client.post("/v1/integrations/health/sync", headers=headers)
    assert sync.status_code == 200, sync.text
    assert seen_tokens == ["ya29.access"]
    assert sync.json() == {
        "weight_written": 1,
        "body_fat_written": 0,
        "daily_metrics_written": 1,
    }

    # The weight reading landed in body_metrics.
    sm = get_sessionmaker()
    async with sm() as session:
        rows = (
            (await session.execute(select(BodyMetric).where(BodyMetric.recorded_at == recorded_at)))
            .scalars()
            .all()
        )
    assert len(rows) == 1
    assert rows[0].weight_kg == Decimal("76.66")

    # The steps reading landed in daily_metrics for its local day.
    from app.models.daily_metric import DailyMetric

    async with sm() as session:
        daily = (
            (await session.execute(select(DailyMetric).where(DailyMetric.date == metric_day)))
            .scalars()
            .all()
        )
    assert len(daily) == 1
    assert daily[0].steps == 8000

    # A second sync of the same reading is idempotent for body_metrics (no
    # duplicate row); the daily upsert re-applies (on-conflict update) so its
    # count reflects rows touched, not just inserted.
    sync_again = await client.post("/v1/integrations/health/sync", headers=headers)
    assert sync_again.json() == {
        "weight_written": 0,
        "body_fat_written": 0,
        "daily_metrics_written": 1,
    }
    async with sm() as session:
        daily_after = (
            (await session.execute(select(DailyMetric).where(DailyMetric.date == metric_day)))
            .scalars()
            .all()
        )
    assert len(daily_after) == 1

    # Disconnect removes the connection row.
    disconnect = await client.delete("/v1/integrations/health", headers=headers)
    assert disconnect.status_code == 204
    final = (await client.get("/v1/integrations/health/status", headers=headers)).json()
    assert final["connected"] is False


async def test_auth_error_flags_needs_reauth_and_reconnect_clears_it(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dead token (GoogleHealthAuthError on sync) flips needs_reauth -> the
    status endpoint surfaces it + /sync returns 409 -> reconnecting clears it."""
    headers = await _sign_in(client, monkeypatch, sub="reauth-sub")

    # Connect with a token that's already expired so the sync forces a refresh.
    auth = (
        await client.post(
            "/v1/integrations/health/authorize",
            headers=headers,
            json={"code_challenge": "challenge-" + "z" * 32},
        )
    ).json()
    expired = gh_client.GoogleHealthTokens(
        access_token="ya29.expired",
        refresh_token="1//dead-refresh",
        expires_at=datetime.now(tz=UTC) - timedelta(minutes=1),  # already expired
        scopes=gh_client.DEFAULT_SCOPES,
        google_user_id="google-reauth",
    )

    async def fake_exchange(**kw: Any) -> gh_client.GoogleHealthTokens:
        return expired

    monkeypatch.setattr(gh_client, "exchange_code", fake_exchange)
    await client.post(
        "/v1/integrations/health/callback",
        headers=headers,
        json={
            "code": "auth-code",
            "state": auth["state"],
            "code_verifier": "verifier-" + "z" * 40,
        },
    )

    status_after_connect = (
        await client.get("/v1/integrations/health/status", headers=headers)
    ).json()
    assert status_after_connect["connected"] is True
    assert status_after_connect["needs_reauth"] is False

    # The token refresh fails with a dead refresh token -> GoogleHealthAuthError.
    async def fake_refresh(**kw: Any) -> gh_client.GoogleHealthTokens:
        raise gh_client.GoogleHealthAuthError("invalid_grant")

    monkeypatch.setattr(gh_client, "refresh_tokens", fake_refresh)

    sync = await client.post("/v1/integrations/health/sync", headers=headers)
    assert sync.status_code == 409, sync.text

    # Status now reports needs_reauth so the client can prompt a reconnect.
    flagged = (await client.get("/v1/integrations/health/status", headers=headers)).json()
    assert flagged["connected"] is True
    assert flagged["needs_reauth"] is True

    # Reconnecting (fresh, valid token) clears the flag.
    auth2 = (
        await client.post(
            "/v1/integrations/health/authorize",
            headers=headers,
            json={"code_challenge": "challenge-" + "w" * 32},
        )
    ).json()
    fresh = gh_client.GoogleHealthTokens(
        access_token="ya29.fresh",
        refresh_token="1//fresh-refresh",
        expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
        scopes=gh_client.DEFAULT_SCOPES,
        google_user_id="google-reauth",
    )

    async def fake_exchange2(**kw: Any) -> gh_client.GoogleHealthTokens:
        return fresh

    monkeypatch.setattr(gh_client, "exchange_code", fake_exchange2)
    await client.post(
        "/v1/integrations/health/callback",
        headers=headers,
        json={
            "code": "auth-code-2",
            "state": auth2["state"],
            "code_verifier": "verifier-" + "w" * 40,
        },
    )

    cleared = (await client.get("/v1/integrations/health/status", headers=headers)).json()
    assert cleared["needs_reauth"] is False


# ---------------------------------------------------------------------------
# incremental read window: compute_since + early-stop pagination
# ---------------------------------------------------------------------------


def test_compute_since_first_sync_uses_backfill_window() -> None:
    # No last_synced_at => read from roughly now - BACKFILL_DAYS.
    before = datetime.now(tz=UTC)
    since = gh_client.compute_since(None)
    after = datetime.now(tz=UTC)
    expected_lo = before - timedelta(days=gh_client.BACKFILL_DAYS)
    expected_hi = after - timedelta(days=gh_client.BACKFILL_DAYS)
    assert expected_lo <= since <= expected_hi


def test_compute_since_incremental_subtracts_overlap() -> None:
    last = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    assert gh_client.compute_since(last) == last - gh_client.OVERLAP


async def test_list_data_points_early_stops_on_all_older_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Newest-first pagination must stop after a full page with no point >= since.

    Page 1 has a point newer than ``since`` (keep going); page 2 is entirely
    older (stop). Page 3 must never be requested even though page 2 returns a
    nextPageToken.
    """
    since = datetime(2026, 6, 5, 0, 0, 0, tzinfo=UTC)

    def steps_point(iso: str) -> dict[str, Any]:
        return {"steps": {"interval": {"startTime": iso}, "count": "1"}}

    pages: dict[str | None, tuple[list[dict[str, Any]], str | None]] = {
        # Page 1: mixed (one newer-or-equal than since) -> keep going.
        None: ([steps_point("2026-06-06T10:00:00Z"), steps_point("2026-06-04T10:00:00Z")], "tok2"),
        # Page 2: all older than since -> early-stop (despite a nextPageToken).
        "tok2": (
            [steps_point("2026-06-03T10:00:00Z"), steps_point("2026-06-02T10:00:00Z")],
            "tok3",
        ),
        # Page 3 must never be fetched.
        "tok3": ([steps_point("2026-06-01T10:00:00Z")], None),
    }
    requested: list[str | None] = []

    async def fake_get_page(
        *, access_token: str, data_type: str, page_token: str | None
    ) -> tuple[list[dict[str, Any]], str | None]:
        requested.append(page_token)
        return pages[page_token]

    monkeypatch.setattr(gh_client, "_get_data_points_page", fake_get_page)

    collected = await gh_client._list_data_points(
        access_token="tok",
        data_type=gh_client.STEPS_DATA_TYPE,
        since=since,
        point_time=gh_client._steps_point_time,
    )

    # Pages 1 and 2 were fetched; page 3 (token "tok3") was never requested.
    assert requested == [None, "tok2"]
    assert "tok3" not in requested
    assert len(collected) == 4
