"""Tests for the personal-records timeline endpoint GET /v1/me/prs."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.db import get_sessionmaker
from app.services import auth as auth_service


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "prs-sub"
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _make_exercise(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    name: str,
) -> dict[str, Any]:
    payload = {
        "name": name,
        "primary_muscle": "chest",
        "secondary_muscles": ["triceps"],
        "equipment": "barbell",
        "movement_pattern": "horizontal_push",
        "tracking_type": "weight_reps",
        "is_unilateral": False,
    }
    return (await client.post("/v1/exercises", headers=headers, json=payload)).json()


async def _log_session_on_date(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    on_date: date,
    exercises: list[dict[str, Any]],
) -> str:
    session = (await client.post("/v1/workout-sessions", headers=headers, json={})).json()
    sm = get_sessionmaker()
    async with sm() as db:
        await db.execute(
            text("UPDATE workout_sessions SET started_at = :ts WHERE id = :id"),
            {
                "ts": datetime.combine(on_date, datetime.min.time().replace(hour=12), tzinfo=UTC),
                "id": session["id"],
            },
        )
        await db.commit()
    for ex in exercises:
        we = (
            await client.post(
                f"/v1/workout-sessions/{session['id']}/exercises",
                headers=headers,
                json={"exercise_id": ex["exercise_id"]},
            )
        ).json()
        for s in ex["sets"]:
            await client.post(
                f"/v1/workout-exercises/{we['id']}/sets",
                headers=headers,
                json={
                    "weight_kg": s.get("weight_kg"),
                    "reps": s.get("reps"),
                    "rpe": s.get("rpe"),
                    "set_type": s.get("set_type", "working"),
                },
            )
    finish = await client.post(f"/v1/workout-sessions/{session['id']}/finish", headers=headers)
    assert finish.status_code == 200, finish.text
    return session["id"]


async def test_empty_timeline_for_user_with_no_prs(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="prs-empty")
    response = await client.get("/v1/me/prs", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["items"] == []
    assert body["next_cursor"] is None


async def test_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/v1/me/prs")
    assert response.status_code == 401


async def test_first_pr_has_null_delta_and_carries_links(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="prs-first")
    ex = await _make_exercise(client, headers, name="Bench")
    today = date.today()
    # 100 x 5 -> e1rm = 100 * (1 + 5/30) = 116.67. First PR ever -> delta null.
    session_id = await _log_session_on_date(
        client,
        headers,
        on_date=today,
        exercises=[{"exercise_id": ex["id"], "sets": [{"weight_kg": "100", "reps": 5}]}],
    )

    response = await client.get("/v1/me/prs", headers=headers)
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) == 1
    event = items[0]
    assert event["exercise_id"] == ex["id"]
    assert event["exercise_name"] == "Bench"
    assert event["session_id"] == session_id
    assert Decimal(event["weight_kg"]) == Decimal("100.00")
    assert event["reps"] == 5
    assert Decimal(event["e1rm_kg"]) == Decimal("116.67")
    assert event["e1rm_delta_kg"] is None


async def test_delta_against_previous_pr_for_same_exercise(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="prs-delta")
    ex = await _make_exercise(client, headers, name="Squat")
    today = date.today()
    # PR #1: 100 x 5 -> e1rm 116.67 (delta null).
    await _log_session_on_date(
        client,
        headers,
        on_date=today - timedelta(days=14),
        exercises=[{"exercise_id": ex["id"], "sets": [{"weight_kg": "100", "reps": 5}]}],
    )
    # 90 x 5 -> e1rm 105.00: not a PR, should not appear.
    await _log_session_on_date(
        client,
        headers,
        on_date=today - timedelta(days=10),
        exercises=[{"exercise_id": ex["id"], "sets": [{"weight_kg": "90", "reps": 5}]}],
    )
    # PR #2: 105 x 5 -> e1rm 122.50; delta = 122.50 - 116.67 = 5.83.
    await _log_session_on_date(
        client,
        headers,
        on_date=today,
        exercises=[{"exercise_id": ex["id"], "sets": [{"weight_kg": "105", "reps": 5}]}],
    )

    items = (await client.get("/v1/me/prs", headers=headers)).json()["items"]
    # Newest first; only the two PRs.
    assert len(items) == 2
    assert Decimal(items[0]["e1rm_kg"]) == Decimal("122.50")
    assert Decimal(items[0]["e1rm_delta_kg"]) == Decimal("5.83")
    assert Decimal(items[1]["e1rm_kg"]) == Decimal("116.67")
    assert items[1]["e1rm_delta_kg"] is None


async def test_timeline_spans_multiple_exercises_newest_first(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="prs-multi")
    bench = await _make_exercise(client, headers, name="Bench")
    squat = await _make_exercise(client, headers, name="Squat")
    today = date.today()
    await _log_session_on_date(
        client,
        headers,
        on_date=today - timedelta(days=5),
        exercises=[{"exercise_id": bench["id"], "sets": [{"weight_kg": "100", "reps": 5}]}],
    )
    await _log_session_on_date(
        client,
        headers,
        on_date=today,
        exercises=[{"exercise_id": squat["id"], "sets": [{"weight_kg": "140", "reps": 3}]}],
    )

    items = (await client.get("/v1/me/prs", headers=headers)).json()["items"]
    assert len(items) == 2
    # Squat is most recent -> first.
    assert items[0]["exercise_name"] == "Squat"
    assert items[1]["exercise_name"] == "Bench"
    # Both first PRs for their exercise -> null deltas.
    assert items[0]["e1rm_delta_kg"] is None
    assert items[1]["e1rm_delta_kg"] is None


async def test_pagination_with_cursor(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    headers = await _sign_in(client, monkeypatch, sub="prs-page")
    today = date.today()
    # Three exercises, each PR on a distinct day so ordering is deterministic.
    names = ["Ex-A", "Ex-B", "Ex-C"]
    for i, name in enumerate(names):
        ex = await _make_exercise(client, headers, name=name)
        await _log_session_on_date(
            client,
            headers,
            on_date=today - timedelta(days=i),
            exercises=[{"exercise_id": ex["id"], "sets": [{"weight_kg": "100", "reps": 5}]}],
        )

    page1 = (await client.get("/v1/me/prs?limit=2", headers=headers)).json()
    assert len(page1["items"]) == 2
    assert page1["next_cursor"] is not None
    # Newest first: Ex-A (today), Ex-B (yesterday).
    assert page1["items"][0]["exercise_name"] == "Ex-A"
    assert page1["items"][1]["exercise_name"] == "Ex-B"

    page2 = (
        await client.get(f"/v1/me/prs?limit=2&cursor={page1['next_cursor']}", headers=headers)
    ).json()
    assert len(page2["items"]) == 1
    assert page2["items"][0]["exercise_name"] == "Ex-C"
    assert page2["next_cursor"] is None


async def test_invalid_cursor_returns_400(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="prs-badcursor")
    response = await client.get("/v1/me/prs?cursor=not-a-real-cursor", headers=headers)
    assert response.status_code == 400


async def test_prs_scoped_to_requesting_user(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers_a = await _sign_in(client, monkeypatch, sub="prs-owner")
    ex = await _make_exercise(client, headers_a, name="Bench")
    await _log_session_on_date(
        client,
        headers_a,
        on_date=date.today(),
        exercises=[{"exercise_id": ex["id"], "sets": [{"weight_kg": "100", "reps": 5}]}],
    )
    # Different user should see no PRs.
    headers_b = await _sign_in(client, monkeypatch, sub="prs-other")
    items = (await client.get("/v1/me/prs", headers=headers_b)).json()["items"]
    assert items == []
