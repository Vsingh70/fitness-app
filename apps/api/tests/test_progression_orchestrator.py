"""End-to-end: a scheduled-session finish writes the right recommendation."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db import get_sessionmaker
from app.models.exercise_progression import ExerciseProgression
from app.models.recommendation import Recommendation
from app.services import auth as auth_service


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "prog-sub"
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _exercise_payload() -> dict[str, Any]:
    return {
        "name": "Bench Press (test)",
        "primary_muscle": "chest",
        "secondary_muscles": ["triceps"],
        "equipment": "barbell",
        "movement_pattern": "horizontal_push",
        "tracking_type": "weight_reps",
        "is_unilateral": False,
    }


async def _create_program_with_one_exercise(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    exercise_id: str,
    progression: str,
    target_reps_low: int,
    target_reps_high: int | None = None,
) -> str:
    program = (
        await client.post(
            "/v1/programs",
            headers=headers,
            json={
                "name": "Prog test",
                "goal": "strength",
                "weeks": 4,
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
            "target_reps_low": target_reps_low,
            "target_reps_high": target_reps_high,
            "progression_strategy": progression,
        },
    )
    return program["id"]


async def _activate(client: AsyncClient, headers: dict[str, str], program_id: str) -> None:
    response = await client.post(
        f"/v1/programs/{program_id}/activate",
        headers=headers,
        json={"start_date": "2026-06-01", "weekday_offset": 0, "skip_existing": True},
    )
    assert response.status_code == 200, response.text


async def _log_session_at_weight(
    client: AsyncClient,
    headers: dict[str, str],
    scheduled_id: str,
    *,
    weight: str,
    reps_per_set: list[int],
) -> dict[str, Any]:
    """Start the scheduled workout, log working sets, finish."""
    workout = (
        await client.post(f"/v1/scheduled-workouts/{scheduled_id}/start", headers=headers)
    ).json()
    we_id = workout["workout_exercises"][0]["id"]
    for reps in reps_per_set:
        await client.post(
            f"/v1/workout-exercises/{we_id}/sets",
            headers=headers,
            json={"weight_kg": weight, "reps": reps, "set_type": "working"},
        )
    finish = await client.post(f"/v1/workout-sessions/{workout['id']}/finish", headers=headers)
    assert finish.status_code == 200, finish.text
    return finish.json()


async def test_linear_progression_writes_increase_weight_recommendation(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    program_id = await _create_program_with_one_exercise(
        client,
        headers,
        exercise_id=exercise["id"],
        progression="linear",
        target_reps_low=5,
    )
    await _activate(client, headers, program_id)
    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    assert len(scheduled) == 4  # 4 weeks * 1 day

    # Hit 5/5/5 at 60 kg.
    await _log_session_at_weight(
        client, headers, scheduled[0]["id"], weight="60", reps_per_set=[5, 5, 5]
    )

    # Recommendation written, attached to the next planned scheduled workout.
    recs = (await client.get("/v1/recommendations", headers=headers)).json()["items"]
    assert len(recs) == 1
    rec = recs[0]
    assert rec["kind"] == "increase_weight"
    assert rec["suggested_weight_kg"] == "62.50"
    assert rec["suggested_reps_low"] == 5
    assert rec["scheduled_workout_id"] == scheduled[1]["id"]

    # And the progression row reflects the new state.
    sm = get_sessionmaker()
    async with sm() as session:
        prog = (
            await session.execute(
                select(ExerciseProgression).where(ExerciseProgression.exercise_id == exercise["id"])
            )
        ).scalar_one()
    assert prog.current_top_set_weight_kg == Decimal("62.50")
    assert prog.consecutive_successes == 1
    assert prog.consecutive_failures == 0


async def test_two_consecutive_failures_trigger_deload(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    program_id = await _create_program_with_one_exercise(
        client,
        headers,
        exercise_id=exercise["id"],
        progression="linear",
        target_reps_low=5,
    )
    await _activate(client, headers, program_id)
    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]

    # Session 1: miss (5/5/4 at 100).
    await _log_session_at_weight(
        client, headers, scheduled[0]["id"], weight="100", reps_per_set=[5, 5, 4]
    )
    recs = (await client.get("/v1/recommendations", headers=headers)).json()["items"]
    assert recs[0]["kind"] == "increase_reps"  # holding weight, target reps unchanged
    assert recs[0]["suggested_weight_kg"] == "100.00"

    # Session 2: miss again -> deload 10% = 90.00.
    await _log_session_at_weight(
        client, headers, scheduled[1]["id"], weight="100", reps_per_set=[5, 5, 4]
    )
    recs = (await client.get("/v1/recommendations", headers=headers)).json()["items"]
    assert len(recs) == 1
    rec = recs[0]
    assert rec["kind"] == "deload"
    assert rec["suggested_weight_kg"] == "90.00"


async def test_double_progression_advances_at_top_of_range(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    program_id = await _create_program_with_one_exercise(
        client,
        headers,
        exercise_id=exercise["id"],
        progression="double_progression",
        target_reps_low=8,
        target_reps_high=12,
    )
    await _activate(client, headers, program_id)
    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]

    await _log_session_at_weight(
        client, headers, scheduled[0]["id"], weight="60", reps_per_set=[12, 12, 12]
    )
    recs = (await client.get("/v1/recommendations", headers=headers)).json()["items"]
    assert recs[0]["kind"] == "increase_weight"
    assert recs[0]["suggested_weight_kg"] == "62.50"
    assert recs[0]["suggested_reps_low"] == 8
    assert recs[0]["suggested_reps_high"] == 12


async def test_consume_and_dismiss_endpoints(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    program_id = await _create_program_with_one_exercise(
        client,
        headers,
        exercise_id=exercise["id"],
        progression="linear",
        target_reps_low=5,
    )
    await _activate(client, headers, program_id)
    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    await _log_session_at_weight(
        client, headers, scheduled[0]["id"], weight="60", reps_per_set=[5, 5, 5]
    )
    rec = (await client.get("/v1/recommendations", headers=headers)).json()["items"][0]

    consume = await client.post(f"/v1/recommendations/{rec['id']}/consume", headers=headers)
    assert consume.status_code == 200
    assert consume.json()["consumed_at"] is not None

    # After consuming, the list endpoint omits it.
    after = (await client.get("/v1/recommendations", headers=headers)).json()["items"]
    assert all(r["id"] != rec["id"] for r in after)

    # Dismiss a fresh rec by simulating another finished session.
    await _log_session_at_weight(
        client, headers, scheduled[1]["id"], weight="62.5", reps_per_set=[5, 5, 5]
    )
    rec2 = (await client.get("/v1/recommendations", headers=headers)).json()["items"][0]
    dismiss = await client.post(f"/v1/recommendations/{rec2['id']}/dismiss", headers=headers)
    assert dismiss.status_code == 200
    assert dismiss.json()["dismissed_at"] is not None


async def test_per_scheduled_workout_recommendation_lookup(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    program_id = await _create_program_with_one_exercise(
        client,
        headers,
        exercise_id=exercise["id"],
        progression="linear",
        target_reps_low=5,
    )
    await _activate(client, headers, program_id)
    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    await _log_session_at_weight(
        client, headers, scheduled[0]["id"], weight="60", reps_per_set=[5, 5, 5]
    )

    # The rec should be attached to scheduled[1].
    response = await client.get(
        f"/v1/scheduled-workouts/{scheduled[1]['id']}/recommendations",
        headers=headers,
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["scheduled_workout_id"] == scheduled[1]["id"]


async def test_auto_apply_produces_and_consumes_recommendation(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Audit (API-5): finishing a scheduled workout runs the auto-apply path,
    which both PRODUCES a fresh rec for the next scheduled workout AND CONSUMES
    (sets consumed_at) the rec that was attached to the just-finished workout.

    The existing tests only cover the "produced" half. This covers the full
    produce-and-consume cycle that the orchestrator performs inline on finish,
    confirming the auto-apply path is wired (event-driven on finish, per
    tasks/04-progression/01-linear-double.md) and that consumed_at is set
    without any manual /consume call.
    """
    headers = await _sign_in(client, monkeypatch, sub="prog-auto-consume")
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    program_id = await _create_program_with_one_exercise(
        client,
        headers,
        exercise_id=exercise["id"],
        progression="linear",
        target_reps_low=5,
    )
    await _activate(client, headers, program_id)
    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    assert len(scheduled) >= 3

    # Session 1: success -> PRODUCES a rec attached to scheduled[1].
    await _log_session_at_weight(
        client, headers, scheduled[0]["id"], weight="60", reps_per_set=[5, 5, 5]
    )
    recs = (await client.get("/v1/recommendations", headers=headers)).json()["items"]
    assert len(recs) == 1
    rec_for_s1 = recs[0]
    assert rec_for_s1["scheduled_workout_id"] == scheduled[1]["id"]
    assert rec_for_s1["consumed_at"] is None  # still active before its workout runs

    # Session 2: finishing scheduled[1] auto-CONSUMES the rec that pointed at it
    # AND PRODUCES a new rec for scheduled[2] -- all inside the finish call,
    # with no manual /consume.
    await _log_session_at_weight(
        client, headers, scheduled[1]["id"], weight="62.5", reps_per_set=[5, 5, 5]
    )

    # Active list now holds only the freshly-produced rec for scheduled[2].
    active = (await client.get("/v1/recommendations", headers=headers)).json()["items"]
    assert len(active) == 1
    assert active[0]["id"] != rec_for_s1["id"]
    assert active[0]["scheduled_workout_id"] == scheduled[2]["id"]

    # The rec produced after session 1 is now consumed (applied) automatically.
    sm = get_sessionmaker()
    async with sm() as session:
        consumed = (
            await session.execute(
                select(Recommendation).where(Recommendation.id == UUID(rec_for_s1["id"]))
            )
        ).scalar_one()
    assert consumed.consumed_at is not None, (
        "auto-apply path must set consumed_at on the rec attached to the "
        "just-finished scheduled workout"
    )
    assert consumed.dismissed_at is None


async def test_free_style_session_writes_no_recommendation(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sessions not linked to a scheduled workout should produce no recs."""
    headers = await _sign_in(client, monkeypatch)
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    session = (await client.post("/v1/workout-sessions", headers=headers, json={})).json()
    we = (
        await client.post(
            f"/v1/workout-sessions/{session['id']}/exercises",
            headers=headers,
            json={"exercise_id": exercise["id"]},
        )
    ).json()
    await client.post(
        f"/v1/workout-exercises/{we['id']}/sets",
        headers=headers,
        json={"weight_kg": "60", "reps": 5},
    )
    await client.post(f"/v1/workout-sessions/{session['id']}/finish", headers=headers)

    sm = get_sessionmaker()
    async with sm() as session_:
        recs = (await session_.execute(select(Recommendation))).scalars().all()
    assert recs == []
