"""Tests for the per-exercise analytics endpoint."""

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
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "ea-sub"
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
    primary: str = "chest",
    secondary: list[str] | None = None,
    equipment: str = "barbell",
    movement_pattern: str = "horizontal_push",
    tracking_type: str = "weight_reps",
) -> dict[str, Any]:
    payload = {
        "name": name,
        "primary_muscle": primary,
        "secondary_muscles": secondary or ["triceps"],
        "equipment": equipment,
        "movement_pattern": movement_pattern,
        "tracking_type": tracking_type,
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


async def test_window_query_validation(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    ex = await _make_exercise(client, headers, name="Bench")
    response = await client.get(f"/v1/analytics/exercises/{ex['id']}?window=foo", headers=headers)
    assert response.status_code == 400


async def test_e1rm_and_volume_series_for_three_sessions(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    ex = await _make_exercise(client, headers, name="Bench")
    today = date.today()
    # Session 1: 100 x 5 -> e1rm = 100 * (1 + 5/30) = 116.67; tonnage 500.
    await _log_session_on_date(
        client,
        headers,
        on_date=today - timedelta(days=14),
        exercises=[
            {"exercise_id": ex["id"], "sets": [{"weight_kg": "100", "reps": 5, "rpe": "7"}]}
        ],
    )
    # Session 2: 100 x 6 -> e1rm = 100 * 1.2 = 120.00; tonnage 600.
    await _log_session_on_date(
        client,
        headers,
        on_date=today - timedelta(days=7),
        exercises=[
            {"exercise_id": ex["id"], "sets": [{"weight_kg": "100", "reps": 6, "rpe": "8"}]}
        ],
    )
    # Session 3: 105 x 5 -> e1rm = 105 * 1.1667 = 122.50; tonnage 525.
    await _log_session_on_date(
        client,
        headers,
        on_date=today,
        exercises=[
            {"exercise_id": ex["id"], "sets": [{"weight_kg": "105", "reps": 5, "rpe": "8"}]}
        ],
    )

    response = await client.get(f"/v1/analytics/exercises/{ex['id']}?window=4w", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    e1rm = body["e1rm_series"]
    volume = body["volume_series"]
    rpe = body["avg_rpe_series"]
    assert len(e1rm) == 3
    assert Decimal(e1rm[0]["value"]) == Decimal("116.67")
    assert Decimal(e1rm[1]["value"]) == Decimal("120.00")
    assert Decimal(e1rm[2]["value"]) == Decimal("122.50")
    assert Decimal(volume[0]["value"]) == Decimal("500.00")
    assert Decimal(volume[1]["value"]) == Decimal("600.00")
    assert Decimal(volume[2]["value"]) == Decimal("525.00")
    assert Decimal(rpe[0]["value"]) == Decimal("7.00")
    assert Decimal(rpe[2]["value"]) == Decimal("8.00")


async def test_window_filters_old_sessions(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    ex = await _make_exercise(client, headers, name="Bench")
    today = date.today()
    # Old session, 20 weeks ago - excluded by 12w window.
    await _log_session_on_date(
        client,
        headers,
        on_date=today - timedelta(weeks=20),
        exercises=[{"exercise_id": ex["id"], "sets": [{"weight_kg": "60", "reps": 5}]}],
    )
    # Recent session.
    await _log_session_on_date(
        client,
        headers,
        on_date=today - timedelta(days=3),
        exercises=[{"exercise_id": ex["id"], "sets": [{"weight_kg": "100", "reps": 5}]}],
    )
    response = await client.get(f"/v1/analytics/exercises/{ex['id']}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["e1rm_series"]) == 1


async def test_warmup_sets_excluded_from_series(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    ex = await _make_exercise(client, headers, name="Bench")
    today = date.today()
    await _log_session_on_date(
        client,
        headers,
        on_date=today,
        exercises=[
            {
                "exercise_id": ex["id"],
                "sets": [
                    {"weight_kg": "60", "reps": 10, "set_type": "warmup"},
                    {"weight_kg": "100", "reps": 5, "set_type": "working"},
                ],
            }
        ],
    )
    response = await client.get(f"/v1/analytics/exercises/{ex['id']}", headers=headers)
    body = response.json()
    assert len(body["e1rm_series"]) == 1
    # Only the working set: e1rm = 100 * (1 + 5/30) = 116.67
    assert Decimal(body["e1rm_series"][0]["value"]) == Decimal("116.67")
    # Volume = 100 * 5 = 500 (warmup excluded)
    assert Decimal(body["volume_series"][0]["value"]) == Decimal("500.00")
    # Scatter excludes warmup.
    assert all(s["reps"] == 5 for s in body["set_scatter"])


async def test_recent_prs_surfaced(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    headers = await _sign_in(client, monkeypatch)
    ex = await _make_exercise(client, headers, name="Bench")
    today = date.today()
    # Each session strictly improves e1rm -> each set should be marked PR.
    await _log_session_on_date(
        client,
        headers,
        on_date=today - timedelta(days=14),
        exercises=[{"exercise_id": ex["id"], "sets": [{"weight_kg": "100", "reps": 5}]}],
    )
    await _log_session_on_date(
        client,
        headers,
        on_date=today,
        exercises=[{"exercise_id": ex["id"], "sets": [{"weight_kg": "110", "reps": 5}]}],
    )
    response = await client.get(f"/v1/analytics/exercises/{ex['id']}", headers=headers)
    body = response.json()
    assert len(body["recent_prs"]) == 2
    # Newest first.
    assert Decimal(body["recent_prs"][0]["weight_kg"]) == Decimal("110.00")
    # Scatter points for PR sets should be flagged is_pr=true.
    pr_set = next(s for s in body["set_scatter"] if Decimal(s["weight_kg"]) == Decimal("110.00"))
    assert pr_set["is_pr"] is True


async def test_predicted_next_session_matches_orchestrator(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After a finished scheduled session, the recommendation row drives the
    predicted_next_session field on this endpoint.
    """
    headers = await _sign_in(client, monkeypatch)
    ex = await _make_exercise(client, headers, name="Bench")

    program = (
        await client.post(
            "/v1/programs",
            headers=headers,
            json={
                "name": "EA prog",
                "goal": "strength",
                "weeks": 2,
                "days_per_week": 1,
            },
        )
    ).json()
    day = (
        await client.post(
            f"/v1/programs/{program['id']}/days",
            headers=headers,
            json={"name": "Day 1"},
        )
    ).json()
    await client.post(
        f"/v1/program-days/{day['id']}/exercises",
        headers=headers,
        json={
            "exercise_id": ex["id"],
            "target_sets": 3,
            "target_reps_low": 5,
            "progression_strategy": "linear",
        },
    )
    await client.post(
        f"/v1/programs/{program['id']}/activate",
        headers=headers,
        json={"start_date": "2026-06-01", "weekday_offset": 0, "skip_existing": True},
    )
    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]

    workout = (
        await client.post(f"/v1/scheduled-workouts/{scheduled[0]['id']}/start", headers=headers)
    ).json()
    we_id = workout["workout_exercises"][0]["id"]
    for _ in range(3):
        await client.post(
            f"/v1/workout-exercises/{we_id}/sets",
            headers=headers,
            json={"weight_kg": "60", "reps": 5, "set_type": "working"},
        )
    finish = await client.post(f"/v1/workout-sessions/{workout['id']}/finish", headers=headers)
    assert finish.status_code == 200

    response = await client.get(f"/v1/analytics/exercises/{ex['id']}", headers=headers)
    body = response.json()
    pred = body["predicted_next_session"]
    assert pred["has_prediction"] is True
    assert pred["source"] == "recommendation"
    assert pred["kind"] == "increase_weight"
    assert Decimal(pred["suggested_weight_kg"]) == Decimal("62.50")


async def test_predicted_next_session_falls_back_to_progression(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When no active rec exists but exercise_progression has rolling state,
    surface that as the prediction.
    """
    headers = await _sign_in(client, monkeypatch)
    ex = await _make_exercise(client, headers, name="Bench")
    today = date.today()
    # A free-style session creates exercise_progression via PR detection.
    await _log_session_on_date(
        client,
        headers,
        on_date=today - timedelta(days=2),
        exercises=[{"exercise_id": ex["id"], "sets": [{"weight_kg": "100", "reps": 5}]}],
    )
    # Hand-seed current_top_set_weight_kg on the progression row so we have
    # a deterministic value to assert on.
    sm = get_sessionmaker()
    async with sm() as db:
        await db.execute(
            text(
                "UPDATE exercise_progression "
                "SET current_top_set_weight_kg = 100, current_target_reps_low = 5 "
                "WHERE exercise_id = :ex_id"
            ),
            {"ex_id": ex["id"]},
        )
        await db.commit()

    response = await client.get(f"/v1/analytics/exercises/{ex['id']}", headers=headers)
    body = response.json()
    pred = body["predicted_next_session"]
    assert pred["has_prediction"] is True
    assert pred["source"] == "progression"
    assert Decimal(pred["suggested_weight_kg"]) == Decimal("100.00")
    assert pred["suggested_reps_low"] == 5


async def test_predicted_next_session_none_when_no_data(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    ex = await _make_exercise(client, headers, name="Bench")
    response = await client.get(f"/v1/analytics/exercises/{ex['id']}", headers=headers)
    body = response.json()
    assert body["predicted_next_session"]["has_prediction"] is False
    assert body["predicted_next_session"]["source"] == "none"


async def test_suggested_variants_ranked_by_usage_then_name(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same primary muscle + movement pattern, different equipment, ranked by
    times the user has logged each (desc), then by name ascending.
    """
    headers = await _sign_in(client, monkeypatch)
    primary = await _make_exercise(client, headers, name="Barbell Bench", equipment="barbell")
    # Variants share primary muscle (chest) and movement (horizontal_push) but
    # have different equipment.
    db_press = await _make_exercise(client, headers, name="Dumbbell Bench", equipment="dumbbell")
    machine_press = await _make_exercise(
        client, headers, name="Machine Chest Press", equipment="machine"
    )
    # Unrelated: different movement_pattern -> should NOT appear.
    await _make_exercise(
        client,
        headers,
        name="Overhead Press",
        equipment="dumbbell",
        movement_pattern="vertical_push",
    )

    today = date.today()
    # Log db_press once, machine_press twice -> machine first.
    await _log_session_on_date(
        client,
        headers,
        on_date=today - timedelta(days=3),
        exercises=[{"exercise_id": db_press["id"], "sets": [{"weight_kg": "20", "reps": 8}]}],
    )
    await _log_session_on_date(
        client,
        headers,
        on_date=today - timedelta(days=2),
        exercises=[{"exercise_id": machine_press["id"], "sets": [{"weight_kg": "40", "reps": 8}]}],
    )
    await _log_session_on_date(
        client,
        headers,
        on_date=today - timedelta(days=1),
        exercises=[{"exercise_id": machine_press["id"], "sets": [{"weight_kg": "40", "reps": 8}]}],
    )

    response = await client.get(f"/v1/analytics/exercises/{primary['id']}", headers=headers)
    variants = response.json()["suggested_variants"]
    names = [v["exercise"]["name"] for v in variants]
    assert names[0] == "Machine Chest Press"
    assert names[1] == "Dumbbell Bench"
    assert "Overhead Press" not in names
    # Verify the primary exercise itself is excluded.
    assert "Barbell Bench" not in names


async def test_exercise_not_found_returns_404(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    from uuid import uuid4

    response = await client.get(f"/v1/analytics/exercises/{uuid4()}", headers=headers)
    assert response.status_code == 404
