"""Push workouts to Fitbit: mapping, idempotency, opt-out, manual trigger."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.clients import fitbit as fitbit_client
from app.db import get_sessionmaker
from app.models.workout import WorkoutSession
from app.services import auth as auth_service


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "fp-sub"
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _stub_tokens() -> fitbit_client.FitbitTokens:
    return fitbit_client.FitbitTokens(
        access_token="fb-access-1",
        refresh_token="fb-refresh-1",
        expires_at=datetime.now(tz=UTC) + timedelta(hours=8),
        scopes=["activity"],
        fitbit_user_id="fitbit-user-987",
    )


async def _connect_fitbit(
    client: AsyncClient, headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    auth = (
        await client.post(
            "/v1/integrations/fitbit/authorize",
            headers=headers,
            json={"code_challenge": "challenge-" + "x" * 32},
        )
    ).json()

    async def fake_exchange(**kw: Any) -> fitbit_client.FitbitTokens:
        return _stub_tokens()

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


async def _make_exercise(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    name: str,
    movement_pattern: str = "horizontal_push",
) -> dict[str, Any]:
    payload = {
        "name": name,
        "primary_muscle": "chest",
        "secondary_muscles": ["triceps"],
        "equipment": "barbell",
        "movement_pattern": movement_pattern,
        "tracking_type": "weight_reps",
        "is_unilateral": False,
    }
    return (await client.post("/v1/exercises", headers=headers, json=payload)).json()


async def _build_session(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    name: str = "Test session",
    movement_pattern: str = "horizontal_push",
) -> str:
    """Create a session with one exercise + 3 working sets, do not finish."""
    exercise = await _make_exercise(
        client, headers, name=f"{name}-ex", movement_pattern=movement_pattern
    )
    session = (
        await client.post("/v1/workout-sessions", headers=headers, json={"name": name})
    ).json()
    we = (
        await client.post(
            f"/v1/workout-sessions/{session['id']}/exercises",
            headers=headers,
            json={"exercise_id": exercise["id"]},
        )
    ).json()
    for _ in range(3):
        await client.post(
            f"/v1/workout-exercises/{we['id']}/sets",
            headers=headers,
            json={"weight_kg": "100", "reps": 5, "set_type": "working"},
        )
    return session["id"]


def _stub_post_activity_result(log_id: str = "111222333") -> fitbit_client.FitbitPostActivityResult:
    return fitbit_client.FitbitPostActivityResult(
        log_id=log_id,
        raw={"activityLog": {"logId": log_id}},
    )


# ---------------------------------------------------------------------------
# Auto-push on finish
# ---------------------------------------------------------------------------


async def test_finish_session_auto_pushes_when_connected(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    await _connect_fitbit(client, headers, monkeypatch)
    session_id = await _build_session(client, headers)

    calls: list[dict[str, Any]] = []

    async def fake_post(**kw: Any) -> fitbit_client.FitbitPostActivityResult:
        calls.append(kw)
        return _stub_post_activity_result()

    monkeypatch.setattr(fitbit_client, "post_activity", fake_post)

    finish = await client.post(f"/v1/workout-sessions/{session_id}/finish", headers=headers)
    assert finish.status_code == 200

    assert len(calls) == 1
    # Strength session -> activityId 3001.
    assert calls[0]["activity_id"] == 3001
    # Persisted log id + pushed-at.
    sm = get_sessionmaker()
    async with sm() as db:
        record = (
            await db.execute(select(WorkoutSession).where(WorkoutSession.id == session_id))
        ).scalar_one()
    assert record.fitbit_log_id == "111222333"
    assert record.fitbit_pushed_at is not None


async def test_finish_session_skips_when_auto_push_disabled(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    await _connect_fitbit(client, headers, monkeypatch)
    # Flip the user toggle off.
    await client.patch("/v1/me", headers=headers, json={"auto_push_to_fitbit": False})
    session_id = await _build_session(client, headers)

    async def fake_post(**kw: Any) -> Any:
        raise AssertionError("post_activity should not be called when auto-push is disabled")

    monkeypatch.setattr(fitbit_client, "post_activity", fake_post)

    finish = await client.post(f"/v1/workout-sessions/{session_id}/finish", headers=headers)
    assert finish.status_code == 200

    sm = get_sessionmaker()
    async with sm() as db:
        record = (
            await db.execute(select(WorkoutSession).where(WorkoutSession.id == session_id))
        ).scalar_one()
    assert record.fitbit_log_id is None
    assert record.fitbit_pushed_at is None


async def test_finish_session_skips_when_no_connection(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    session_id = await _build_session(client, headers)

    async def fake_post(**kw: Any) -> Any:
        raise AssertionError("post_activity should not be called when not connected")

    monkeypatch.setattr(fitbit_client, "post_activity", fake_post)

    finish = await client.post(f"/v1/workout-sessions/{session_id}/finish", headers=headers)
    assert finish.status_code == 200


# ---------------------------------------------------------------------------
# Manual trigger + idempotency
# ---------------------------------------------------------------------------


async def test_manual_push_endpoint(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    headers = await _sign_in(client, monkeypatch)
    await _connect_fitbit(client, headers, monkeypatch)
    # Disable auto-push so finish doesn't already push.
    await client.patch("/v1/me", headers=headers, json={"auto_push_to_fitbit": False})
    session_id = await _build_session(client, headers)
    await client.post(f"/v1/workout-sessions/{session_id}/finish", headers=headers)

    async def fake_post(**kw: Any) -> fitbit_client.FitbitPostActivityResult:
        return _stub_post_activity_result(log_id="555")

    monkeypatch.setattr(fitbit_client, "post_activity", fake_post)

    response = await client.post(
        f"/v1/workout-sessions/{session_id}/push-to-fitbit", headers=headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["pushed"] is True
    assert body["fitbit_log_id"] == "555"


async def test_manual_push_is_idempotent(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    await _connect_fitbit(client, headers, monkeypatch)
    session_id = await _build_session(client, headers)

    call_count = {"n": 0}

    async def fake_post(**kw: Any) -> fitbit_client.FitbitPostActivityResult:
        call_count["n"] += 1
        return _stub_post_activity_result(log_id="999")

    monkeypatch.setattr(fitbit_client, "post_activity", fake_post)
    await client.post(f"/v1/workout-sessions/{session_id}/finish", headers=headers)
    # First push happened on finish. Manual trigger should short-circuit.
    second = await client.post(f"/v1/workout-sessions/{session_id}/push-to-fitbit", headers=headers)
    assert second.status_code == 200
    assert second.json()["skipped_reason"] == "already_pushed"
    assert call_count["n"] == 1


async def test_409_marks_pushed_without_log_id(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    await _connect_fitbit(client, headers, monkeypatch)
    session_id = await _build_session(client, headers)

    async def fake_post(**kw: Any) -> Any:
        raise fitbit_client.FitbitDuplicateError("activity already logged")

    monkeypatch.setattr(fitbit_client, "post_activity", fake_post)
    finish = await client.post(f"/v1/workout-sessions/{session_id}/finish", headers=headers)
    assert finish.status_code == 200

    sm = get_sessionmaker()
    async with sm() as db:
        record = (
            await db.execute(select(WorkoutSession).where(WorkoutSession.id == session_id))
        ).scalar_one()
    assert record.fitbit_pushed_at is not None
    assert record.fitbit_log_id is None  # 409 means we never got a log id from Fitbit


async def test_auth_failure_does_not_mark_pushed(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    await _connect_fitbit(client, headers, monkeypatch)
    session_id = await _build_session(client, headers)

    async def fake_post(**kw: Any) -> Any:
        raise fitbit_client.FitbitAuthError("401")

    monkeypatch.setattr(fitbit_client, "post_activity", fake_post)
    await client.post(f"/v1/workout-sessions/{session_id}/finish", headers=headers)

    sm = get_sessionmaker()
    async with sm() as db:
        record = (
            await db.execute(select(WorkoutSession).where(WorkoutSession.id == session_id))
        ).scalar_one()
    assert record.fitbit_pushed_at is None
    assert record.fitbit_log_id is None


# ---------------------------------------------------------------------------
# fitbit-link DELETE
# ---------------------------------------------------------------------------


async def test_delete_fitbit_link_clears_columns(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    await _connect_fitbit(client, headers, monkeypatch)
    session_id = await _build_session(client, headers)

    async def fake_post(**kw: Any) -> fitbit_client.FitbitPostActivityResult:
        return _stub_post_activity_result(log_id="abc")

    monkeypatch.setattr(fitbit_client, "post_activity", fake_post)
    await client.post(f"/v1/workout-sessions/{session_id}/finish", headers=headers)

    response = await client.delete(
        f"/v1/workout-sessions/{session_id}/fitbit-link", headers=headers
    )
    assert response.status_code == 204

    sm = get_sessionmaker()
    async with sm() as db:
        record = (
            await db.execute(select(WorkoutSession).where(WorkoutSession.id == session_id))
        ).scalar_one()
    assert record.fitbit_log_id is None
    assert record.fitbit_pushed_at is None


# ---------------------------------------------------------------------------
# Cardio mapping
# ---------------------------------------------------------------------------


async def test_cardio_session_uses_cardio_activity_id(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    await _connect_fitbit(client, headers, monkeypatch)
    session_id = await _build_session(client, headers, name="cardio", movement_pattern="cardio")

    calls: list[dict[str, Any]] = []

    async def fake_post(**kw: Any) -> fitbit_client.FitbitPostActivityResult:
        calls.append(kw)
        return _stub_post_activity_result()

    monkeypatch.setattr(fitbit_client, "post_activity", fake_post)
    await client.post(f"/v1/workout-sessions/{session_id}/finish", headers=headers)
    assert calls[0]["activity_id"] != 3001  # cardio, not strength
    assert calls[0]["activity_id"] == 90013


# ---------------------------------------------------------------------------
# Me schema includes the new toggle
# ---------------------------------------------------------------------------


async def test_me_includes_auto_push_to_fitbit(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    me = (await client.get("/v1/me", headers=headers)).json()
    assert me["auto_push_to_fitbit"] is True
    await client.patch("/v1/me", headers=headers, json={"auto_push_to_fitbit": False})
    me2 = (await client.get("/v1/me", headers=headers)).json()
    assert me2["auto_push_to_fitbit"] is False
