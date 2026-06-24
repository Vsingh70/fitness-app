"""Task B (06 + 05): structured-work endpoints, finish-advances-rotation, skip,
and the temporary one-session swap.

Covers:
- set_segments: rest-pause/cluster/myo sub-bouts (``mini_set``) and the
  segment-summed reps for analytics.
- interval sets: ``set_type=interval`` with ``rounds`` + work/rest segments.
- ``workout_exercises.block_kind`` / ``block_label`` round-trip.
- ``users.default_rest_seconds`` GET/PATCH default + override on /me.
- finishing a program-linked session advances the program rotation pointer;
  a freestyle session does NOT advance anything (there is no pointer to move).
- ``POST .../skip`` marks the linked scheduled workout ``skipped``, advances the
  rotation neutrally, runs no progression, and keeps already-logged sets.
- ``POST .../swap`` sets ``substituted_for_exercise_id`` so the original pauses.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db import get_sessionmaker
from app.models.enums import ScheduledWorkoutStatus
from app.models.exercise_progression import ExerciseProgression
from app.models.scheduled_workout import ScheduledWorkout
from app.services import auth as auth_service
from tests._scheduling_helpers import seed_scheduled_for_program


async def _sign_in(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    sub: str = "structured-sub",
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _exercise_payload(
    *,
    name: str,
    tracking_type: str = "weight_reps",
    primary: str = "chest",
    equipment: str = "barbell",
    movement: str = "horizontal_push",
) -> dict[str, Any]:
    return {
        "name": name,
        "primary_muscle": primary,
        "secondary_muscles": [],
        "equipment": equipment,
        "movement_pattern": movement,
        "tracking_type": tracking_type,
        "is_unilateral": False,
    }


async def _create_exercise(
    client: AsyncClient, headers: dict[str, str], **kwargs: Any
) -> dict[str, Any]:
    resp = await client.post("/v1/exercises", headers=headers, json=_exercise_payload(**kwargs))
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _empty_session(client: AsyncClient, headers: dict[str, str]) -> str:
    return (await client.post("/v1/workout-sessions", headers=headers, json={})).json()["id"]


async def _add_exercise(
    client: AsyncClient,
    headers: dict[str, str],
    session_id: str,
    exercise_id: str,
    **extra: Any,
) -> dict[str, Any]:
    body = {"exercise_id": exercise_id, **extra}
    resp = await client.post(
        f"/v1/workout-sessions/{session_id}/exercises", headers=headers, json=body
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Set segments: rest-pause / cluster / myo (mini_set) sub-bouts.
# ---------------------------------------------------------------------------


async def test_set_with_mini_set_segments_sums_reps(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A rest-pause set 10+3+2 stores three ``mini_set`` segments; total reps for
    analytics is the sum (15). The top-level required-field check is skipped when
    the create payload carries segments."""
    headers = await _sign_in(client, monkeypatch, sub="seg-sub")
    exercise = await _create_exercise(client, headers, name="RP Bench")
    session_id = await _empty_session(client, headers)
    we = await _add_exercise(client, headers, session_id, exercise["id"])

    resp = await client.post(
        f"/v1/workout-exercises/{we['id']}/sets",
        headers=headers,
        json={
            "set_type": "myo_rep",
            "weight_kg": "80",
            "segments": [
                {"kind": "mini_set", "reps": 10, "weight_kg": "80"},
                {"kind": "rest", "rest_seconds": 15},
                {"kind": "mini_set", "reps": 3, "weight_kg": "80"},
                {"kind": "rest", "rest_seconds": 15},
                {"kind": "mini_set", "reps": 2, "weight_kg": "80"},
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    created = resp.json()
    assert created["set_type"] == "myo_rep"
    segments = created["segments"]
    assert len(segments) == 5
    # Index defaults to list position.
    assert [s["segment_index"] for s in segments] == [0, 1, 2, 3, 4]
    mini = [s for s in segments if s["kind"] == "mini_set"]
    assert sum(s["reps"] for s in mini) == 15

    # Round-trips on the nested GET too.
    full = (await client.get(f"/v1/workout-sessions/{session_id}", headers=headers)).json()
    got = full["workout_exercises"][0]["sets"][0]["segments"]
    assert sum(s["reps"] for s in got if s["kind"] == "mini_set") == 15


async def test_set_with_segments_skips_required_field_check(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cluster set carries its load/reps in segments, so the top-level
    reps/weight required-field check is skipped when segments are present."""
    headers = await _sign_in(client, monkeypatch, sub="seg-skip-sub")
    exercise = await _create_exercise(client, headers, name="Cluster Bench")
    session_id = await _empty_session(client, headers)
    we = await _add_exercise(client, headers, session_id, exercise["id"])

    resp = await client.post(
        f"/v1/workout-exercises/{we['id']}/sets",
        headers=headers,
        json={
            "set_type": "cluster",
            "segments": [
                {"kind": "mini_set", "reps": 3, "weight_kg": "100"},
                {"kind": "mini_set", "reps": 3, "weight_kg": "100"},
            ],
        },
    )
    assert resp.status_code == 201, resp.text


# ---------------------------------------------------------------------------
# Interval sets: rounds + work/rest segments.
# ---------------------------------------------------------------------------


async def test_interval_set_stores_rounds_and_work_rest_segments(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="interval-sub")
    exercise = await _create_exercise(
        client,
        headers,
        name="Assault Bike Intervals",
        tracking_type="time_only",
        primary="quads",
        equipment="cardio_machine",
        movement="cardio",
    )
    session_id = await _empty_session(client, headers)
    we = await _add_exercise(client, headers, session_id, exercise["id"])

    resp = await client.post(
        f"/v1/workout-exercises/{we['id']}/sets",
        headers=headers,
        json={
            "set_type": "interval",
            "rounds": 8,
            "segments": [
                {"kind": "work", "duration_seconds": 30, "distance_meters": "150"},
                {"kind": "rest", "duration_seconds": 15},
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    created = resp.json()
    assert created["set_type"] == "interval"
    assert created["rounds"] == 8
    kinds = [s["kind"] for s in created["segments"]]
    assert kinds == ["work", "rest"]
    work = next(s for s in created["segments"] if s["kind"] == "work")
    assert work["duration_seconds"] == 30
    assert work["distance_meters"] == "150.00"


# ---------------------------------------------------------------------------
# Block kind / block label round-trip.
# ---------------------------------------------------------------------------


async def test_block_kind_and_label_round_trip(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="block-sub")
    mobility = await _create_exercise(
        client,
        headers,
        name="Hip Opener",
        tracking_type="time_only",
        primary="glutes",
        equipment="bodyweight",
        movement="mobility",
    )
    session_id = await _empty_session(client, headers)

    # Default block_kind is "working".
    working = await _add_exercise(client, headers, session_id, mobility["id"])
    assert working["block_kind"] == "working"
    assert working["block_label"] is None

    # Explicit warm-up block with a label.
    warmup = await _add_exercise(
        client,
        headers,
        session_id,
        mobility["id"],
        block_kind="warmup",
        block_label="Mobility",
    )
    assert warmup["block_kind"] == "warmup"
    assert warmup["block_label"] == "Mobility"

    # PATCH can move it to cooldown.
    patched = (
        await client.patch(
            f"/v1/workout-exercises/{warmup['id']}",
            headers=headers,
            json={"block_kind": "cooldown"},
        )
    ).json()
    assert patched["block_kind"] == "cooldown"


# ---------------------------------------------------------------------------
# users.default_rest_seconds preference (GET/PATCH on /me).
# ---------------------------------------------------------------------------


async def test_default_rest_seconds_default_and_patch(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="rest-pref-sub")

    me = (await client.get("/v1/me", headers=headers)).json()
    assert me["default_rest_seconds"] == 90  # seeded default

    patched = (
        await client.patch("/v1/me", headers=headers, json={"default_rest_seconds": 120})
    ).json()
    assert patched["default_rest_seconds"] == 120

    me_again = (await client.get("/v1/me", headers=headers)).json()
    assert me_again["default_rest_seconds"] == 120


# ---------------------------------------------------------------------------
# Finish advances the program rotation; freestyle does not.
# ---------------------------------------------------------------------------


async def _build_program_with_exercise(
    client: AsyncClient, headers: dict[str, str], exercise_id: str
) -> str:
    program = (
        await client.post(
            "/v1/programs", headers=headers, json={"name": "RotProg", "goal": "general"}
        )
    ).json()
    day = (
        await client.post(
            f"/v1/programs/{program['id']}/slots", headers=headers, json={"name": "Day 1"}
        )
    ).json()
    await client.post(
        f"/v1/program-slots/{day['id']}/exercises",
        headers=headers,
        json={
            "exercise_id": exercise_id,
            "target_sets": 3,
            "target_reps_low": 5,
            "progression_strategy": "linear",
        },
    )
    # A second (rest) slot gives microcycle_length=2, so advancing the rotation
    # pointer moves slot 0 -> 1 cleanly (rather than wrapping a 1-slot microcycle
    # into the next repetition).
    await client.post(
        f"/v1/programs/{program['id']}/slots",
        headers=headers,
        json={"name": "Rest", "is_rest_day": True},
    )
    activate = await client.post(f"/v1/programs/{program['id']}/activate", headers=headers)
    assert activate.status_code == 200, activate.text
    await seed_scheduled_for_program(program["id"], count=4, start=datetime.now(UTC).date())
    return str(program["id"])


async def test_finish_program_session_advances_rotation(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="finish-advance-sub")
    exercise = await _create_exercise(client, headers, name="Prog Bench")
    program_id = await _build_program_with_exercise(client, headers, exercise["id"])

    before = (await client.get(f"/v1/programs/{program_id}/position", headers=headers)).json()
    assert before["current_slot_index"] == 0
    assert before["current_repetition"] == 1

    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    start = await client.post(f"/v1/scheduled-workouts/{scheduled[0]['id']}/start", headers=headers)
    workout = start.json()
    we_id = workout["workout_exercises"][0]["id"]
    await client.post(
        f"/v1/workout-exercises/{we_id}/sets",
        headers=headers,
        json={"weight_kg": "60", "reps": 5, "set_type": "working"},
    )

    finish = await client.post(f"/v1/workout-sessions/{workout['id']}/finish", headers=headers)
    assert finish.status_code == 200, finish.text

    # Completing the slot consumed it: the rotation pointer advanced.
    after = (await client.get(f"/v1/programs/{program_id}/position", headers=headers)).json()
    assert after["current_slot_index"] == before["current_slot_index"] + 1

    # The linked scheduled workout is marked completed.
    sm = get_sessionmaker()
    async with sm() as db:
        sw = (
            await db.execute(
                select(ScheduledWorkout).where(
                    ScheduledWorkout.id == workout["scheduled_workout_id"]
                )
            )
        ).scalar_one()
    assert sw.status == ScheduledWorkoutStatus.completed


async def test_finish_freestyle_session_does_not_advance_rotation(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A freestyle session has no scheduled link, so finishing it never touches a
    rotation pointer — but per-exercise progression still tracks (PR on first
    working set)."""
    headers = await _sign_in(client, monkeypatch, sub="freestyle-sub")
    exercise = await _create_exercise(client, headers, name="Free Bench")
    program_id = await _build_program_with_exercise(client, headers, exercise["id"])

    before = (await client.get(f"/v1/programs/{program_id}/position", headers=headers)).json()

    # A separate, freestyle session (no scheduled_workout_id).
    session_id = await _empty_session(client, headers)
    we = await _add_exercise(client, headers, session_id, exercise["id"])
    await client.post(
        f"/v1/workout-exercises/{we['id']}/sets",
        headers=headers,
        json={"weight_kg": "100", "reps": 5},
    )
    finish = await client.post(f"/v1/workout-sessions/{session_id}/finish", headers=headers)
    assert finish.status_code == 200

    after = (await client.get(f"/v1/programs/{program_id}/position", headers=headers)).json()
    assert after["current_slot_index"] == before["current_slot_index"]
    assert after["current_repetition"] == before["current_repetition"]

    # Freestyle work still moved the lift: a PR was detected.
    full = (await client.get(f"/v1/workout-sessions/{session_id}", headers=headers)).json()
    assert full["workout_exercises"][0]["sets"][0]["is_pr"] is True


# ---------------------------------------------------------------------------
# Skip: advances neutrally, marks skipped, no progression, sets kept.
# ---------------------------------------------------------------------------


async def test_skip_advances_neutrally_and_marks_skipped(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="skip-sub")
    exercise = await _create_exercise(client, headers, name="Skip Bench")
    program_id = await _build_program_with_exercise(client, headers, exercise["id"])

    before = (await client.get(f"/v1/programs/{program_id}/position", headers=headers)).json()

    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    workout = (
        await client.post(f"/v1/scheduled-workouts/{scheduled[0]['id']}/start", headers=headers)
    ).json()
    we_id = workout["workout_exercises"][0]["id"]
    # Log a partial set; it must survive the skip.
    await client.post(
        f"/v1/workout-exercises/{we_id}/sets",
        headers=headers,
        json={"weight_kg": "60", "reps": 5, "set_type": "working"},
    )

    skip = await client.post(f"/v1/workout-sessions/{workout['id']}/skip", headers=headers)
    assert skip.status_code == 200, skip.text
    skipped = skip.json()
    assert skipped["ended_at"] is not None
    # Already-logged set is kept on the (now skipped) session.
    assert len(skipped["workout_exercises"][0]["sets"]) == 1

    # The rotation pointer advanced (slot consumed, not repeated).
    after = (await client.get(f"/v1/programs/{program_id}/position", headers=headers)).json()
    assert after["current_slot_index"] == before["current_slot_index"] + 1

    # The scheduled workout is marked skipped.
    sm = get_sessionmaker()
    async with sm() as db:
        sw = (
            await db.execute(
                select(ScheduledWorkout).where(
                    ScheduledWorkout.id == workout["scheduled_workout_id"]
                )
            )
        ).scalar_one()
        assert sw.status == ScheduledWorkoutStatus.skipped

        # Skip is neutral: no progression ran, so no recommendation and no
        # progression-state advance for the exercise.
        prog = (
            await db.execute(
                select(ExerciseProgression).where(ExerciseProgression.exercise_id == exercise["id"])
            )
        ).scalar_one_or_none()
    assert prog is None  # progression never ran for a skip

    recs = (await client.get("/v1/recommendations", headers=headers)).json()["items"]
    assert recs == []


# ---------------------------------------------------------------------------
# Temp swap: original pauses (substituted_for_exercise_id), sets credit substitute.
# ---------------------------------------------------------------------------


async def test_temp_swap_records_original_and_redirects_logging(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="swap-sub")
    barbell = await _create_exercise(client, headers, name="Barbell Bench")
    dumbbell = await _create_exercise(client, headers, name="Dumbbell Bench", equipment="dumbbell")
    session_id = await _empty_session(client, headers)
    we = await _add_exercise(client, headers, session_id, barbell["id"])
    assert we["exercise_id"] == barbell["id"]
    assert we["substituted_for_exercise_id"] is None

    swap = await client.post(
        f"/v1/workout-exercises/{we['id']}/swap",
        headers=headers,
        json={"substitute_exercise_id": dumbbell["id"]},
    )
    assert swap.status_code == 200, swap.text
    swapped = swap.json()
    # Now logs against the substitute; the original is recorded so it pauses.
    assert swapped["exercise_id"] == dumbbell["id"]
    assert swapped["substituted_for_exercise_id"] == barbell["id"]

    # Logged sets count to the substitute (validated against its tracking_type).
    set_resp = await client.post(
        f"/v1/workout-exercises/{we['id']}/sets",
        headers=headers,
        json={"weight_kg": "30", "reps": 10},
    )
    assert set_resp.status_code == 201, set_resp.text


async def test_swap_to_same_exercise_is_rejected(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="swap-same-sub")
    bench = await _create_exercise(client, headers, name="Bench")
    session_id = await _empty_session(client, headers)
    we = await _add_exercise(client, headers, session_id, bench["id"])

    resp = await client.post(
        f"/v1/workout-exercises/{we['id']}/swap",
        headers=headers,
        json={"substitute_exercise_id": bench["id"]},
    )
    assert resp.status_code == 422
