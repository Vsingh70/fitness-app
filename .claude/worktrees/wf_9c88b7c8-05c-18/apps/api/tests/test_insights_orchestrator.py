"""Integration tests for the insight heuristic orchestrator and endpoints.

These tests seed sessions/sets directly via the REST API (and a tiny bit of
direct SQL to backdate started_at), then either call the recompute endpoint
or wait for the autouse rollup fixture to run rollups inline.
"""

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
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    sub: str = "ins-sub",
    sex_at_birth: str | None = "male",
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    if sex_at_birth is not None:
        await client.patch("/v1/me", headers=headers, json={"sex_at_birth": sex_at_birth})
    return headers


async def _make_exercise(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    name: str,
    primary: str,
    secondary: list[str],
    tracking_type: str = "weight_reps",
    movement_pattern: str = "horizontal_push",
) -> dict[str, Any]:
    payload = {
        "name": name,
        "primary_muscle": primary,
        "secondary_muscles": secondary,
        "equipment": "barbell",
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
    bodyweight_kg: str | None = "80",
) -> str:
    """Create a free-style session, backdate started_at to `on_date`, log sets, finish."""
    session = (await client.post("/v1/workout-sessions", headers=headers, json={})).json()
    sm = get_sessionmaker()
    async with sm() as db:
        await db.execute(
            text(
                "UPDATE workout_sessions SET started_at = :ts, bodyweight_kg = :bw WHERE id = :id"
            ),
            {
                "ts": datetime.combine(on_date, datetime.min.time().replace(hour=12), tzinfo=UTC),
                "bw": Decimal(bodyweight_kg) if bodyweight_kg is not None else None,
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
                    "set_type": s.get("set_type", "working"),
                },
            )
    finish = await client.post(f"/v1/workout-sessions/{session['id']}/finish", headers=headers)
    assert finish.status_code == 200, finish.text
    return session["id"]


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


async def test_strong_chest_moderate_quads_at_acceptance_ratios(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Acceptance criterion: bench at 1.5x BW flags chest as strong;
    squat at 1.0x BW does NOT flag quads as strong (lands in moderate band).
    """
    headers = await _sign_in(client, monkeypatch, sub="strong-sub")
    bench = await _make_exercise(
        client,
        headers,
        name="Barbell Bench Press",
        primary="chest",
        secondary=["triceps"],
        movement_pattern="horizontal_push",
    )
    squat = await _make_exercise(
        client,
        headers,
        name="Barbell Back Squat",
        primary="quads",
        secondary=["glutes"],
        movement_pattern="squat",
    )

    target = _monday(date.today())
    # Bench 120 kg x 5 with BW 80 = 120 * (1 + 5/30) = 140 kg e1RM = 1.75x BW (strong).
    await _log_session_on_date(
        client,
        headers,
        on_date=target,
        bodyweight_kg="80",
        exercises=[{"exercise_id": bench["id"], "sets": [{"weight_kg": "120", "reps": 5}]}],
    )
    # Squat 80 kg x 5 with BW 80 = 80 * 1.1667 = 93.33 e1RM = 1.17x BW (moderate).
    await _log_session_on_date(
        client,
        headers,
        on_date=target + timedelta(days=1),
        bodyweight_kg="80",
        exercises=[{"exercise_id": squat["id"], "sets": [{"weight_kg": "80", "reps": 5}]}],
    )

    response = await client.post("/v1/insights/recompute", headers=headers)
    assert response.status_code == 200, response.text

    insights = (await client.get("/v1/insights", headers=headers)).json()["items"]
    kinds_by_subject = {(i["kind"], i["subject"]) for i in insights}
    assert ("strong_muscle", "chest") in kinds_by_subject
    # Quads sit in the moderate band, so no strength insight.
    assert ("strong_muscle", "quads") not in kinds_by_subject
    assert ("weak_muscle", "quads") not in kinds_by_subject


async def test_stagnant_deadlift_emits_stagnation_insight(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Eight sessions of identical 5x180 kg deadlift over 8 weeks -> stagnation."""
    headers = await _sign_in(client, monkeypatch, sub="stag-sub")
    deadlift = await _make_exercise(
        client,
        headers,
        name="Barbell Deadlift",
        primary="hamstrings",
        secondary=["glutes", "lats"],
        movement_pattern="hinge",
    )
    today = date.today()
    for i in range(8):
        await _log_session_on_date(
            client,
            headers,
            on_date=today - timedelta(weeks=8) + timedelta(weeks=i),
            exercises=[
                {
                    "exercise_id": deadlift["id"],
                    "sets": [{"weight_kg": "180", "reps": 5}],
                }
            ],
        )

    await client.post("/v1/insights/recompute", headers=headers)
    items = (await client.get("/v1/insights", headers=headers)).json()["items"]
    stagnation = [i for i in items if i["kind"] == "stagnation"]
    assert any(i["subject"] == "barbell-deadlift" for i in stagnation)


async def test_recompute_is_idempotent_no_duplicates(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Running recompute twice with the same data does not create duplicates."""
    headers = await _sign_in(client, monkeypatch, sub="dedup-sub")
    bench = await _make_exercise(
        client,
        headers,
        name="Barbell Bench Press",
        primary="chest",
        secondary=["triceps"],
    )
    target = _monday(date.today())
    await _log_session_on_date(
        client,
        headers,
        on_date=target,
        bodyweight_kg="80",
        exercises=[{"exercise_id": bench["id"], "sets": [{"weight_kg": "120", "reps": 5}]}],
    )

    await client.post("/v1/insights/recompute", headers=headers)
    first = (await client.get("/v1/insights", headers=headers)).json()["items"]
    first_keys = {(i["kind"], i["subject"]) for i in first}
    assert ("strong_muscle", "chest") in first_keys

    await client.post("/v1/insights/recompute", headers=headers)
    second = (await client.get("/v1/insights", headers=headers)).json()["items"]
    assert len(second) == len(first)
    second_keys = {(i["kind"], i["subject"]) for i in second}
    assert second_keys == first_keys


async def test_dismissed_insight_not_resurfaced_within_cooldown(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="dismiss-sub")
    bench = await _make_exercise(
        client,
        headers,
        name="Barbell Bench Press",
        primary="chest",
        secondary=["triceps"],
    )
    target = _monday(date.today())
    await _log_session_on_date(
        client,
        headers,
        on_date=target,
        bodyweight_kg="80",
        exercises=[{"exercise_id": bench["id"], "sets": [{"weight_kg": "120", "reps": 5}]}],
    )
    await client.post("/v1/insights/recompute", headers=headers)
    items = (await client.get("/v1/insights", headers=headers)).json()["items"]
    chest = next(i for i in items if i["subject"] == "chest" and i["kind"] == "strong_muscle")

    dismiss = await client.post(f"/v1/insights/{chest['id']}/dismiss", headers=headers)
    assert dismiss.status_code == 200
    assert dismiss.json()["dismissed_at"] is not None

    # Recompute should NOT resurface the dismissed strong_chest insight.
    await client.post("/v1/insights/recompute", headers=headers)
    after = (await client.get("/v1/insights", headers=headers)).json()["items"]
    assert not any(i["kind"] == "strong_muscle" and i["subject"] == "chest" for i in after)

    # But the dismissed row IS visible with dismissed=true.
    dismissed_list = (await client.get("/v1/insights?dismissed=true", headers=headers)).json()[
        "items"
    ]
    assert any(i["kind"] == "strong_muscle" and i["subject"] == "chest" for i in dismissed_list)


async def test_no_bodyweight_skips_strength_insights(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="nobw-sub")
    bench = await _make_exercise(
        client,
        headers,
        name="Barbell Bench Press",
        primary="chest",
        secondary=["triceps"],
    )
    target = _monday(date.today())
    await _log_session_on_date(
        client,
        headers,
        on_date=target,
        bodyweight_kg=None,
        exercises=[{"exercise_id": bench["id"], "sets": [{"weight_kg": "120", "reps": 5}]}],
    )
    await client.post("/v1/insights/recompute", headers=headers)
    items = (await client.get("/v1/insights", headers=headers)).json()["items"]
    assert not any(i["kind"] in ("weak_muscle", "strong_muscle") for i in items)


async def test_list_filters_by_kind_and_severity(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="filter-sub")
    bench = await _make_exercise(
        client,
        headers,
        name="Barbell Bench Press",
        primary="chest",
        secondary=["triceps"],
    )
    target = _monday(date.today())
    await _log_session_on_date(
        client,
        headers,
        on_date=target,
        bodyweight_kg="80",
        exercises=[{"exercise_id": bench["id"], "sets": [{"weight_kg": "120", "reps": 5}]}],
    )
    await client.post("/v1/insights/recompute", headers=headers)

    response = await client.get("/v1/insights?kind=strong_muscle", headers=headers)
    items = response.json()["items"]
    assert all(i["kind"] == "strong_muscle" for i in items)
    assert len(items) >= 1

    # No insights should match this severity filter for the strong_muscle case
    # (we mark strong_muscle as 'info', not 'action').
    response = await client.get("/v1/insights?severity=action", headers=headers)
    no_action_strong = [i for i in response.json()["items"] if i["kind"] == "strong_muscle"]
    assert no_action_strong == []
