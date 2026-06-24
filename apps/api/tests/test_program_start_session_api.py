"""POST /v1/programs/{id}/start-session (06 §1 "Start from a program").

Resolves the program's current rotation slot via ``program_progress`` and:
- 409 if today's slot is a rest day,
- 422 if the program has no slots,
- else creates a workout_session LINKED to the program + slot (so finishing
  advances the rotation) pre-filled with the slot's exercises and ``target_sets``
  blank set rows as guidance.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db import get_sessionmaker
from app.models.enums import ScheduledWorkoutStatus
from app.models.scheduled_workout import ScheduledWorkout
from app.services import auth as auth_service


async def _sign_in(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    sub: str = "start-session-sub",
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _exercise_payload(*, name: str) -> dict[str, Any]:
    return {
        "name": name,
        "primary_muscle": "chest",
        "secondary_muscles": [],
        "equipment": "barbell",
        "movement_pattern": "horizontal_push",
        "tracking_type": "weight_reps",
        "is_unilateral": False,
    }


async def _create_exercise(client: AsyncClient, headers: dict[str, str], *, name: str) -> str:
    resp = await client.post("/v1/exercises", headers=headers, json=_exercise_payload(name=name))
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


async def _build_program(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    exercise_id: str,
    target_sets: int = 3,
    activate: bool = True,
) -> str:
    """Train / Rest / Train program. The first training slot carries one exercise
    with ``target_sets`` sets."""
    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})
    ).json()
    push = (
        await client.post(
            f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": "Push"}
        )
    ).json()
    await client.post(
        f"/v1/program-slots/{push['id']}/exercises",
        headers=headers,
        json={
            "exercise_id": exercise_id,
            "target_sets": target_sets,
            "target_reps_low": 5,
            "progression_strategy": "linear",
            "notes": "press hard",
        },
    )
    await client.post(
        f"/v1/programs/{prog['id']}/slots",
        headers=headers,
        json={"name": "Rest", "is_rest_day": True},
    )
    await client.post(f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": "Pull"})
    if activate:
        act = await client.post(f"/v1/programs/{prog['id']}/activate", headers=headers)
        assert act.status_code == 200, act.text
    return str(prog["id"])


async def test_start_session_prefills_slot_exercises_and_target_sets(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="start-prefill")
    exercise_id = await _create_exercise(client, headers, name="Bench")
    program_id = await _build_program(client, headers, exercise_id=exercise_id, target_sets=3)

    resp = await client.post(f"/v1/programs/{program_id}/start-session", headers=headers)
    assert resp.status_code == 201, resp.text
    session = resp.json()

    # Linked to a scheduled workout (the slot) so finishing advances the rotation.
    assert session["scheduled_workout_id"] is not None
    assert session["name"] == "Push"

    exercises = session["workout_exercises"]
    assert len(exercises) == 1
    we = exercises[0]
    assert we["exercise_id"] == exercise_id
    assert we["block_kind"] == "working"
    assert we["notes"] == "press hard"
    # target_sets blank set rows as guidance: indices 0..2, no measurements logged.
    assert [s["set_index"] for s in we["sets"]] == [0, 1, 2]
    assert all(s["weight_kg"] is None and s["reps"] is None for s in we["sets"])

    # The scheduled-workout row points at the program + the current slot, marked
    # in_progress, with the rotation position carried over.
    sm = get_sessionmaker()
    async with sm() as db:
        sw = (
            await db.execute(
                select(ScheduledWorkout).where(
                    ScheduledWorkout.id == session["scheduled_workout_id"]
                )
            )
        ).scalar_one()
    assert sw.program_id is not None
    assert sw.program_day_id is not None
    assert sw.status == ScheduledWorkoutStatus.in_progress
    assert sw.microcycle_number == 1
    assert sw.repetition == 1


async def test_start_session_then_finish_advances_rotation(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="start-finish-advance")
    exercise_id = await _create_exercise(client, headers, name="Bench")
    program_id = await _build_program(client, headers, exercise_id=exercise_id)

    before = (await client.get(f"/v1/programs/{program_id}/position", headers=headers)).json()
    assert before["current_slot_index"] == 0
    assert before["today_slot"]["name"] == "Push"

    session = (
        await client.post(f"/v1/programs/{program_id}/start-session", headers=headers)
    ).json()
    we_id = session["workout_exercises"][0]["id"]
    await client.post(
        f"/v1/workout-exercises/{we_id}/sets",
        headers=headers,
        json={"weight_kg": "60", "reps": 5, "set_type": "working"},
    )

    finish = await client.post(f"/v1/workout-sessions/{session['id']}/finish", headers=headers)
    assert finish.status_code == 200, finish.text

    # The slot was consumed: the rotation pointer advanced onto the rest slot.
    after = (await client.get(f"/v1/programs/{program_id}/position", headers=headers)).json()
    assert after["current_slot_index"] == before["current_slot_index"] + 1
    assert after["is_rest_day"] is True

    # The scheduled workout is marked completed.
    sm = get_sessionmaker()
    async with sm() as db:
        sw = (
            await db.execute(
                select(ScheduledWorkout).where(
                    ScheduledWorkout.id == session["scheduled_workout_id"]
                )
            )
        ).scalar_one()
    assert sw.status == ScheduledWorkoutStatus.completed


async def test_start_session_on_rest_day_returns_409(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="start-rest-409")
    exercise_id = await _create_exercise(client, headers, name="Bench")
    program_id = await _build_program(client, headers, exercise_id=exercise_id)

    # Advance off the training slot onto the rest slot (slot_index 1).
    pos = (await client.post(f"/v1/programs/{program_id}/advance", headers=headers)).json()
    assert pos["is_rest_day"] is True

    resp = await client.post(f"/v1/programs/{program_id}/start-session", headers=headers)
    assert resp.status_code == 409, resp.text
    assert "rest" in resp.json()["error"]["message"].lower()

    # No session and no scheduled workout were created for the rest slot.
    sm = get_sessionmaker()
    async with sm() as db:
        count = (await db.execute(select(ScheduledWorkout.id))).scalars().all()
    assert count == []


async def test_start_session_with_no_slots_returns_422(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="start-empty-422")
    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})
    ).json()

    resp = await client.post(f"/v1/programs/{prog['id']}/start-session", headers=headers)
    assert resp.status_code == 422, resp.text


async def test_start_session_requires_ownership(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await _sign_in(client, monkeypatch, sub="start-owner")
    exercise_id = await _create_exercise(client, owner, name="Bench")
    program_id = await _build_program(client, owner, exercise_id=exercise_id)

    other = await _sign_in(client, monkeypatch, sub="start-intruder")
    resp = await client.post(f"/v1/programs/{program_id}/start-session", headers=other)
    assert resp.status_code == 404, resp.text
