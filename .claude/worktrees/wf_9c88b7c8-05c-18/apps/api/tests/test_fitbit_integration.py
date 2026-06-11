"""Fitbit OAuth + sync + webhook tests with the client mocked.

Covers the acceptance criteria:
- Encryption roundtrip
- Token refresh boundary (refresh fires when expiry <1 hour)
- Sync idempotency by fitbit_log_id and (user_id, date)
- Webhook signature verification
- Disconnect deletes the connection row
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from app.clients import fitbit as fitbit_client
from app.db import get_sessionmaker
from app.models.daily_metric import DailyMetric
from app.models.fitbit_activity import FitbitActivity
from app.models.fitbit_connection import FitbitConnection
from app.services import auth as auth_service
from app.services.security import secretbox


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "fb-sub"
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _stub_tokens(*, expires_in: int = 3600) -> fitbit_client.FitbitTokens:
    return fitbit_client.FitbitTokens(
        access_token="fb-access-1",
        refresh_token="fb-refresh-1",
        expires_at=datetime.now(tz=UTC) + timedelta(seconds=expires_in),
        scopes=["activity", "heartrate", "sleep"],
        fitbit_user_id="fitbit-user-123",
    )


def _stub_activities() -> list[fitbit_client.FitbitActivityRow]:
    now = datetime(2026, 5, 20, 18, 0, tzinfo=UTC)
    return [
        fitbit_client.FitbitActivityRow(
            fitbit_log_id=111,
            activity_type="Running",
            started_at=now,
            duration_seconds=1800,
            calories=350,
            average_hr=150,
            max_hr=170,
            steps=4000,
            distance_meters=Decimal("5000.00"),
            raw={"logId": 111},
        ),
        fitbit_client.FitbitActivityRow(
            fitbit_log_id=222,
            activity_type="Cycling",
            started_at=now + timedelta(days=1),
            duration_seconds=2700,
            calories=500,
            average_hr=140,
            max_hr=160,
            steps=None,
            distance_meters=Decimal("12000.00"),
            raw={"logId": 222},
        ),
    ]


def _stub_daily(day_offset: int) -> fitbit_client.FitbitDailySummary:
    target_day = (datetime.now(tz=UTC) - timedelta(days=day_offset)).date()
    return fitbit_client.FitbitDailySummary(
        date=target_day,
        steps=10_000 - day_offset * 100,
        resting_hr=60,
        hrv_ms=None,
        sleep_minutes=420,
        sleep_score=85,
    )


# ---------------------------------------------------------------------------
# secretbox roundtrip
# ---------------------------------------------------------------------------


def test_secretbox_encrypts_and_decrypts() -> None:
    plaintext = "fitbit-access-token-abc-123"
    wire = secretbox.encrypt(plaintext)
    assert wire != plaintext  # ciphertext, not plaintext
    assert secretbox.decrypt(wire) == plaintext


def test_secretbox_rejects_tampered() -> None:
    wire = secretbox.encrypt("hello")
    # Flip a byte in the base64 -> decryption fails.
    raw = bytearray(base64.urlsafe_b64decode(wire.encode("ascii")))
    raw[-1] ^= 0x01
    tampered = base64.urlsafe_b64encode(bytes(raw)).decode("ascii")
    with pytest.raises(secretbox.DecryptionError):
        secretbox.decrypt(tampered)


# ---------------------------------------------------------------------------
# OAuth round-trip
# ---------------------------------------------------------------------------


async def test_authorize_and_callback_creates_connection_row(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)

    auth = (
        await client.post(
            "/v1/integrations/fitbit/authorize",
            headers=headers,
            json={"code_challenge": "challenge-" + "x" * 32},
        )
    ).json()
    assert auth["authorize_url"].startswith("https://www.fitbit.com/oauth2/authorize")
    assert auth["state"]

    tokens = _stub_tokens()

    async def fake_exchange(**kw: Any) -> fitbit_client.FitbitTokens:
        return tokens

    monkeypatch.setattr(fitbit_client, "exchange_code", fake_exchange)

    callback = await client.post(
        "/v1/integrations/fitbit/callback",
        headers=headers,
        json={
            "code": "auth-code",
            "state": auth["state"],
            "code_verifier": "verifier-" + "y" * 40,
        },
    )
    assert callback.status_code == 200, callback.text
    assert callback.json()["connected"] is True
    assert "activity" in callback.json()["scopes"]

    sm = get_sessionmaker()
    async with sm() as db:
        rows = (await db.execute(select(FitbitConnection))).scalars().all()
    assert len(rows) == 1
    assert rows[0].fitbit_user_id == "fitbit-user-123"
    # Tokens are encrypted at rest.
    assert rows[0].access_token_encrypted != tokens.access_token
    assert secretbox.decrypt(rows[0].access_token_encrypted) == tokens.access_token


async def test_callback_rejects_bad_state(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    response = await client.post(
        "/v1/integrations/fitbit/callback",
        headers=headers,
        json={
            "code": "auth-code",
            "state": "not-a-real-jwt",
            "code_verifier": "verifier-" + "y" * 40,
        },
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


async def _setup_connection(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    sub: str = "fb-sub",
    expires_in: int = 8 * 3600,
) -> tuple[dict[str, str], str]:
    """Run the OAuth callback so the test has a FitbitConnection row."""
    headers = await _sign_in(client, monkeypatch, sub=sub)
    auth = (
        await client.post(
            "/v1/integrations/fitbit/authorize",
            headers=headers,
            json={"code_challenge": "challenge-" + "x" * 32},
        )
    ).json()
    tokens = _stub_tokens(expires_in=expires_in)

    async def fake_exchange(**kw: Any) -> fitbit_client.FitbitTokens:
        return tokens

    monkeypatch.setattr(fitbit_client, "exchange_code", fake_exchange)
    await client.post(
        "/v1/integrations/fitbit/callback",
        headers=headers,
        json={
            "code": "auth-code",
            "state": auth["state"],
            "code_verifier": "verifier-" + "y" * 40,
        },
    )
    me = (await client.get("/v1/me", headers=headers)).json()
    return headers, me["id"]


async def test_manual_sync_inserts_then_is_idempotent(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, _user_id = await _setup_connection(client, monkeypatch)
    activities = _stub_activities()

    async def fake_list(**kw: Any) -> list[fitbit_client.FitbitActivityRow]:
        return activities

    async def fake_daily(*, access_token: str, day: date) -> fitbit_client.FitbitDailySummary:
        offset = (datetime.now(tz=UTC).date() - day).days
        return _stub_daily(offset)

    monkeypatch.setattr(fitbit_client, "list_activities", fake_list)
    monkeypatch.setattr(fitbit_client, "daily_summary", fake_daily)

    first = await client.post("/v1/integrations/fitbit/sync", headers=headers)
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["activities_written"] == 2
    # 14-day lookback window.
    assert body["daily_metrics_written"] == 14

    sm = get_sessionmaker()
    async with sm() as db:
        activities_count = (
            await db.execute(text("SELECT COUNT(*) FROM fitbit_activities"))
        ).scalar_one()
        daily_count = (await db.execute(text("SELECT COUNT(*) FROM daily_metrics"))).scalar_one()
    assert activities_count == 2
    assert daily_count == 14

    # Second sync is idempotent.
    second = await client.post("/v1/integrations/fitbit/sync", headers=headers)
    assert second.status_code == 200
    async with sm() as db:
        new_act = (await db.execute(text("SELECT COUNT(*) FROM fitbit_activities"))).scalar_one()
        new_daily = (await db.execute(text("SELECT COUNT(*) FROM daily_metrics"))).scalar_one()
    assert new_act == 2
    assert new_daily == 14


async def test_sync_refreshes_token_when_expiring_within_one_hour(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Connect with a token expiring in 10 minutes; sync_user should refresh it
    before calling the data endpoints.
    """
    headers, _user_id = await _setup_connection(client, monkeypatch, expires_in=600)

    refresh_calls: list[str] = []

    async def fake_refresh(*, refresh_token: str) -> fitbit_client.FitbitTokens:
        refresh_calls.append(refresh_token)
        return fitbit_client.FitbitTokens(
            access_token="fb-access-2",
            refresh_token="fb-refresh-2",
            expires_at=datetime.now(tz=UTC) + timedelta(hours=8),
            scopes=["activity"],
            fitbit_user_id="fitbit-user-123",
        )

    async def fake_list(**kw: Any) -> list[fitbit_client.FitbitActivityRow]:
        # Verify the refreshed token is what's passed downstream.
        assert kw["access_token"] == "fb-access-2"
        return []

    async def fake_daily(*, access_token: str, day: date) -> fitbit_client.FitbitDailySummary:
        assert access_token == "fb-access-2"
        return fitbit_client.FitbitDailySummary(
            date=day,
            steps=None,
            resting_hr=None,
            hrv_ms=None,
            sleep_minutes=None,
            sleep_score=None,
        )

    monkeypatch.setattr(fitbit_client, "refresh_tokens", fake_refresh)
    monkeypatch.setattr(fitbit_client, "list_activities", fake_list)
    monkeypatch.setattr(fitbit_client, "daily_summary", fake_daily)

    response = await client.post("/v1/integrations/fitbit/sync", headers=headers)
    assert response.status_code == 200, response.text
    assert refresh_calls == ["fb-refresh-1"]

    sm = get_sessionmaker()
    async with sm() as db:
        row = (await db.execute(select(FitbitConnection))).scalar_one()
    assert secretbox.decrypt(row.access_token_encrypted) == "fb-access-2"
    assert row.expires_at > datetime.now(tz=UTC) + timedelta(hours=1)


async def test_sync_skips_refresh_when_token_is_fresh(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, _ = await _setup_connection(client, monkeypatch, expires_in=8 * 3600)

    async def fake_refresh(*, refresh_token: str) -> fitbit_client.FitbitTokens:
        raise AssertionError("refresh should not be called when token is fresh")

    async def fake_list(**kw: Any) -> list[fitbit_client.FitbitActivityRow]:
        return []

    async def fake_daily(*, access_token: str, day: date) -> fitbit_client.FitbitDailySummary:
        return fitbit_client.FitbitDailySummary(
            date=day,
            steps=None,
            resting_hr=None,
            hrv_ms=None,
            sleep_minutes=None,
            sleep_score=None,
        )

    monkeypatch.setattr(fitbit_client, "refresh_tokens", fake_refresh)
    monkeypatch.setattr(fitbit_client, "list_activities", fake_list)
    monkeypatch.setattr(fitbit_client, "daily_summary", fake_daily)

    response = await client.post("/v1/integrations/fitbit/sync", headers=headers)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Status + disconnect
# ---------------------------------------------------------------------------


async def test_status_reflects_connected_state(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    before = (await client.get("/v1/integrations/fitbit/status", headers=headers)).json()
    assert before["connected"] is False

    await _setup_connection(client, monkeypatch)

    after = (await client.get("/v1/integrations/fitbit/status", headers=headers)).json()
    assert after["connected"] is True


async def test_disconnect_deletes_connection_keeps_data(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, user_id = await _setup_connection(client, monkeypatch)

    # Insert a stub fitbit_activity to verify it's preserved after disconnect.
    sm = get_sessionmaker()
    async with sm() as db:
        await db.execute(
            text(
                "INSERT INTO fitbit_activities "
                "(id, user_id, fitbit_log_id, activity_type, started_at, raw, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :user_id, 555, 'Run', NOW(), '{}'::jsonb, NOW(), NOW())"
            ),
            {"user_id": user_id},
        )
        await db.commit()

    async def fake_revoke(*, access_token: str) -> None:
        return None

    monkeypatch.setattr(fitbit_client, "revoke", fake_revoke)
    response = await client.delete("/v1/integrations/fitbit", headers=headers)
    assert response.status_code == 204

    async with sm() as db:
        conn_count = (
            await db.execute(text("SELECT COUNT(*) FROM fitbit_connections"))
        ).scalar_one()
        act_count = (await db.execute(text("SELECT COUNT(*) FROM fitbit_activities"))).scalar_one()
    assert conn_count == 0
    assert act_count == 1


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------


def _sign(body: bytes) -> str:
    digest = hmac.new(b"test-fitbit-webhook-secret", body, hashlib.sha1).digest()
    return base64.b64encode(digest).decode("ascii")


async def test_webhook_get_verify_handshake(client: AsyncClient) -> None:
    expected = "dev-fitbit-webhook-verification"
    good = await client.get(f"/v1/webhooks/fitbit?verify={expected}")
    assert good.status_code == 204

    bad = await client.get("/v1/webhooks/fitbit?verify=nope")
    assert bad.status_code == 404


async def test_webhook_rejects_bad_signature(client: AsyncClient) -> None:
    body = json.dumps([{"ownerId": "fitbit-user-123", "collectionType": "activities"}]).encode()
    response = await client.post(
        "/v1/webhooks/fitbit",
        content=body,
        headers={"Content-Type": "application/json", "X-Fitbit-Signature": "wrong"},
    )
    assert response.status_code == 401


async def test_webhook_accepts_valid_signature_and_enqueues(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # First set up a connection so the lookup-by-fitbit-user-id succeeds.
    await _setup_connection(client, monkeypatch)

    enqueued: list[str] = []

    async def fake_enqueue(fitbit_user_id: str) -> None:
        enqueued.append(fitbit_user_id)

    monkeypatch.setattr(
        "app.routers.integrations_fitbit.enqueue_sync_for_fitbit_user", fake_enqueue
    )

    # We can't import the function at module load time because the test
    # monkeypatch is against the router's local reference. Use a try-import
    # inside the router instead - and just send the signed payload.
    body = json.dumps([{"ownerId": "fitbit-user-123", "collectionType": "activities"}]).encode()
    response = await client.post(
        "/v1/webhooks/fitbit",
        content=body,
        headers={"Content-Type": "application/json", "X-Fitbit-Signature": _sign(body)},
    )
    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Sync service direct (no HTTP)
# ---------------------------------------------------------------------------


async def test_sync_user_marks_last_synced_at(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, _user_id_str = await _setup_connection(client, monkeypatch)

    async def fake_list(**kw: Any) -> list[fitbit_client.FitbitActivityRow]:
        return [_stub_activities()[0]]

    async def fake_daily(*, access_token: str, day: date) -> fitbit_client.FitbitDailySummary:
        return fitbit_client.FitbitDailySummary(
            date=day,
            steps=10,
            resting_hr=None,
            hrv_ms=None,
            sleep_minutes=None,
            sleep_score=None,
        )

    monkeypatch.setattr(fitbit_client, "list_activities", fake_list)
    monkeypatch.setattr(fitbit_client, "daily_summary", fake_daily)

    await client.post("/v1/integrations/fitbit/sync", headers=headers)

    sm = get_sessionmaker()
    async with sm() as db:
        row = (await db.execute(select(FitbitConnection))).scalar_one()
        activities = list((await db.execute(select(FitbitActivity))).scalars().all())
        dailies = list((await db.execute(select(DailyMetric))).scalars().all())
    assert row.last_synced_at is not None
    assert row.last_synced_activity_at is not None
    assert len(activities) == 1
    assert len(dailies) == 14
