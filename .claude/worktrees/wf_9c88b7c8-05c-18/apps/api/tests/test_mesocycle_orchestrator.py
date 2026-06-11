"""Integration tests for mesocycle layout, deload behavior, fatigue insights."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db import get_sessionmaker
from app.models.analytics_insight import AnalyticsInsight
from app.models.scheduled_workout import ScheduledWorkout
from app.services import auth as auth_service


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "meso-sub"
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _exercise_payload() -> dict[str, Any]:
    return {
        "name": "Bench (meso test)",
        "primary_muscle": "chest",
        "secondary_muscles": ["triceps"],
        "equipment": "barbell",
        "movement_pattern": "horizontal_push",
        "tracking_type": "weight_reps",
        "is_unilateral": False,
    }


async def _create_program(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    exercise_id: str,
    weeks: int,
    meso_length: int | None = None,
    progression: str = "linear",
    target_reps_low: int = 5,
    target_reps_high: int | None = None,
    target_rpe_low: str | None = None,
    target_rpe_high: str | None = None,
) -> str:
    program = (
        await client.post(
            "/v1/programs",
            headers=headers,
            json={
                "name": "Meso Prog",
                "goal": "strength",
                "weeks": weeks,
                "days_per_week": 1,
            },
        )
    ).json()
    if meso_length is not None:
        await client.patch(
            f"/v1/programs/{program['id']}",
            headers=headers,
            json={"mesocycle_length_weeks": meso_length},
        )
    day = (
        await client.post(
            f"/v1/programs/{program['id']}/days",
            headers=headers,
            json={"name": "Day 1"},
        )
    ).json()
    payload: dict[str, Any] = {
        "exercise_id": exercise_id,
        "target_sets": 3,
        "target_reps_low": target_reps_low,
        "progression_strategy": progression,
    }
    if target_reps_high is not None:
        payload["target_reps_high"] = target_reps_high
    if target_rpe_low is not None:
        payload["target_rpe_low"] = target_rpe_low
    if target_rpe_high is not None:
        payload["target_rpe_high"] = target_rpe_high
    await client.post(
        f"/v1/program-days/{day['id']}/exercises",
        headers=headers,
        json=payload,
    )
    return program["id"]


async def _activate(client: AsyncClient, headers: dict[str, str], program_id: str) -> None:
    response = await client.post(
        f"/v1/programs/{program_id}/activate",
        headers=headers,
        json={"start_date": "2026-06-01", "weekday_offset": 0, "skip_existing": True},
    )
    assert response.status_code == 200, response.text


async def test_8_week_program_meso5_default_layout(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Acceptance criterion: 8 weeks with meso_length=5 puts deload on week 5."""
    headers = await _sign_in(client, monkeypatch)
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    program_id = await _create_program(
        client, headers, exercise_id=exercise["id"], weeks=8, meso_length=5
    )
    await _activate(client, headers, program_id)
    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    assert len(scheduled) == 8
    is_deload = [s["is_deload"] for s in scheduled]
    assert is_deload == [False, False, False, False, True, False, False, False]


async def test_get_program_mesocycle_endpoint(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    program_id = await _create_program(
        client, headers, exercise_id=exercise["id"], weeks=8, meso_length=5
    )
    await _activate(client, headers, program_id)

    response = await client.get(f"/v1/programs/{program_id}/mesocycle", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["mesocycle_length_weeks"] == 5
    assert data["auto_deload"] is True
    assert data["current_week"] is not None
    assert data["week_in_meso"] is not None


async def test_deload_session_writes_hold_recommendation(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Finishing a deload-week session writes a `hold` rec, not increase_weight."""
    headers = await _sign_in(client, monkeypatch)
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    program_id = await _create_program(
        client, headers, exercise_id=exercise["id"], weeks=2, meso_length=2
    )
    await _activate(client, headers, program_id)
    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    # With meso_length=2 and weeks=2: week 1 normal, week 2 deload (since
    # abs_week == program_weeks and week_in_meso == meso_length).
    assert scheduled[0]["is_deload"] is False
    assert scheduled[1]["is_deload"] is True

    # Finish the deload session at a clean 5/5/5 at 100.
    workout = (
        await client.post(f"/v1/scheduled-workouts/{scheduled[1]['id']}/start", headers=headers)
    ).json()
    we_id = workout["workout_exercises"][0]["id"]
    for _ in range(3):
        await client.post(
            f"/v1/workout-exercises/{we_id}/sets",
            headers=headers,
            json={"weight_kg": "100", "reps": 5, "set_type": "working"},
        )
    finish = await client.post(f"/v1/workout-sessions/{workout['id']}/finish", headers=headers)
    assert finish.status_code == 200, finish.text

    # The orchestrator should have emitted a `hold` rec (no next scheduled
    # workout exists, so it has no scheduled_workout_id, which is still
    # surfaced by /v1/recommendations).
    recs = (await client.get("/v1/recommendations", headers=headers)).json()["items"]
    assert len(recs) == 1
    assert recs[0]["kind"] == "hold"
    assert recs[0]["payload"]["is_deload"] is False  # the *next* session is normal


async def test_trigger_deload_marks_current_week_as_deload(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    program_id = await _create_program(
        client, headers, exercise_id=exercise["id"], weeks=4, meso_length=4
    )
    # Activate starting today so the "current week" includes a planned workout.
    from datetime import date, timedelta

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    response = await client.post(
        f"/v1/programs/{program_id}/activate",
        headers=headers,
        json={
            "start_date": monday.isoformat(),
            "weekday_offset": today.weekday(),
            "skip_existing": True,
        },
    )
    assert response.status_code == 200, response.text

    trigger = await client.post(f"/v1/programs/{program_id}/trigger-deload", headers=headers)
    assert trigger.status_code == 200, trigger.text
    body = trigger.json()
    assert body["affected_count"] >= 1
    # Confirm at least one scheduled workout in the current week is_deload=True.
    sm = get_sessionmaker()
    async with sm() as s:
        rows = (
            (
                await s.execute(
                    select(ScheduledWorkout).where(
                        ScheduledWorkout.is_deload.is_(True),
                    )
                )
            )
            .scalars()
            .all()
        )
    assert any(r.is_deload for r in rows)


async def test_high_fatigue_produces_stagnation_insight(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Three sessions of slightly-above RPE on RPE-based progression should
    accumulate fatigue past the 6.0 threshold and write a stagnation insight.
    The 3rd session also triggers a 3-strike deload from the RPE engine; both
    side effects coexist.
    """
    headers = await _sign_in(client, monkeypatch)
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    # weeks=4, meso_length=10 so no deload week kicks in within the program.
    program_id = await _create_program(
        client,
        headers,
        exercise_id=exercise["id"],
        weeks=4,
        meso_length=10,
        progression="rpe_based",
        target_reps_low=5,
        target_reps_high=5,
        target_rpe_low="7",
        target_rpe_high="8",
    )
    await _activate(client, headers, program_id)
    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]

    # Three sessions slightly above (RPE 8.5) + reps below target_low (4) so
    # both over_range AND failed_sets fatigue signals trigger each session.
    # Each session: 1.0 (over_range) + 0.5 * 3 (failed sets) = 2.5
    # After three: 7.5, which exceeds the 6.0 threshold.
    for i in range(3):
        workout = (
            await client.post(f"/v1/scheduled-workouts/{scheduled[i]['id']}/start", headers=headers)
        ).json()
        we_id = workout["workout_exercises"][0]["id"]
        for _ in range(3):
            await client.post(
                f"/v1/workout-exercises/{we_id}/sets",
                headers=headers,
                json={
                    "weight_kg": "100",
                    "reps": 4,
                    "rpe": "8.5",
                    "set_type": "working",
                },
            )
        finish = await client.post(f"/v1/workout-sessions/{workout['id']}/finish", headers=headers)
        assert finish.status_code == 200, finish.text

    # An analytics insight of kind=stagnation severity=action should exist.
    sm = get_sessionmaker()
    async with sm() as s:
        insights = (await s.execute(select(AnalyticsInsight))).scalars().all()
    assert any(i.kind.value == "stagnation" and i.severity.value == "action" for i in insights)
