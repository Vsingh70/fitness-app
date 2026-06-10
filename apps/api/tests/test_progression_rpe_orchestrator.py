"""End-to-end: scheduled-session finish with rpe_based strategy writes the
right recommendation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import AsyncClient

from app.services import auth as auth_service


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "rpe-sub"
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _exercise_payload() -> dict[str, Any]:
    return {
        "name": "RPE Bench (test)",
        "primary_muscle": "chest",
        "secondary_muscles": ["triceps"],
        "equipment": "barbell",
        "movement_pattern": "horizontal_push",
        "tracking_type": "weight_reps",
        "is_unilateral": False,
    }


async def _create_rpe_program(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    exercise_id: str,
    weeks: int = 6,
) -> str:
    program = (
        await client.post(
            "/v1/programs",
            headers=headers,
            json={
                "name": "RPE Prog",
                "goal": "strength",
                "weeks": weeks,
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
            "exercise_id": exercise_id,
            "target_sets": 3,
            "target_reps_low": 5,
            "target_reps_high": 5,
            "target_rpe_low": 7,
            "target_rpe_high": 8,
            "progression_strategy": "rpe_based",
        },
    )
    return program["id"]


async def _activate(client: AsyncClient, headers: dict[str, str], program_id: str) -> None:
    # start today so every scheduled week is future-relative to "now" (a fixed
    # past start_date time-bombs the rec linkage once it passes -- see the note
    # in test_progression_orchestrator._activate).
    start_date = datetime.now(UTC).date().isoformat()
    response = await client.post(
        f"/v1/programs/{program_id}/activate",
        headers=headers,
        json={"start_date": start_date, "weekday_offset": 0, "skip_existing": True},
    )
    assert response.status_code == 200, response.text


async def _log_session_with_rpe(
    client: AsyncClient,
    headers: dict[str, str],
    scheduled_id: str,
    *,
    weight: str,
    reps_per_set: list[int],
    rpe_per_set: list[str],
) -> None:
    workout = (
        await client.post(f"/v1/scheduled-workouts/{scheduled_id}/start", headers=headers)
    ).json()
    we_id = workout["workout_exercises"][0]["id"]
    for reps, rpe in zip(reps_per_set, rpe_per_set, strict=True):
        await client.post(
            f"/v1/workout-exercises/{we_id}/sets",
            headers=headers,
            json={
                "weight_kg": weight,
                "reps": reps,
                "rpe": rpe,
                "set_type": "working",
            },
        )
    finish = await client.post(f"/v1/workout-sessions/{workout['id']}/finish", headers=headers)
    assert finish.status_code == 200, finish.text


async def test_low_rpe_session_recommends_increase_weight(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    program_id = await _create_rpe_program(client, headers, exercise_id=exercise["id"])
    await _activate(client, headers, program_id)
    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    await _log_session_with_rpe(
        client,
        headers,
        scheduled[0]["id"],
        weight="100",
        reps_per_set=[5, 5, 5],
        rpe_per_set=["6", "6", "6"],
    )
    recs = (await client.get("/v1/recommendations", headers=headers)).json()["items"]
    assert len(recs) == 1
    rec = recs[0]
    assert rec["kind"] == "increase_weight"
    assert rec["suggested_weight_kg"] == "102.50"
    assert rec["scheduled_workout_id"] == scheduled[1]["id"]


async def test_far_above_range_recommends_back_off(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    program_id = await _create_rpe_program(client, headers, exercise_id=exercise["id"])
    await _activate(client, headers, program_id)
    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    await _log_session_with_rpe(
        client,
        headers,
        scheduled[0]["id"],
        weight="100",
        reps_per_set=[5, 5, 5],
        rpe_per_set=["9.5", "9.5", "9.5"],
    )
    rec = (await client.get("/v1/recommendations", headers=headers)).json()["items"][0]
    # Back off = 95.00 but the rec kind is `deload` because next_weight < prev_weight.
    assert rec["suggested_weight_kg"] == "95.00"
    assert rec["kind"] == "deload"


async def test_three_consecutive_above_triggers_explicit_deload(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    program_id = await _create_rpe_program(client, headers, exercise_id=exercise["id"], weeks=4)
    await _activate(client, headers, program_id)
    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    # Session 1: slightly above (RPE 8.5) -> hold, consec_above=1.
    await _log_session_with_rpe(
        client,
        headers,
        scheduled[0]["id"],
        weight="100",
        reps_per_set=[5, 5, 5],
        rpe_per_set=["8.5", "8.5", "8.5"],
    )
    # Session 2: slightly above again -> hold, consec_above=2.
    await _log_session_with_rpe(
        client,
        headers,
        scheduled[1]["id"],
        weight="100",
        reps_per_set=[5, 5, 5],
        rpe_per_set=["8.5", "8.5", "8.5"],
    )
    # Session 3: still above -> 3-strike deload (95.00) triggers.
    await _log_session_with_rpe(
        client,
        headers,
        scheduled[2]["id"],
        weight="100",
        reps_per_set=[5, 5, 5],
        rpe_per_set=["8.5", "8.5", "8.5"],
    )
    rec = (await client.get("/v1/recommendations", headers=headers)).json()["items"][0]
    assert rec["kind"] == "deload"
    assert rec["suggested_weight_kg"] == "95.00"
    assert rec["payload"]["is_deload"] is True
