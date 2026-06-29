"""Tests for block_kind / block_label on program_day_exercises.

T5a: Slot exercises in a program can carry block_kind (warmup/working/cooldown)
and block_label. When a session is materialized via POST /programs/{id}/start-session
those values are copied onto the resulting workout_exercise — so a cooldown stretch
declared in the program correctly enters the session as a non-working block and is
excluded from working-volume and PR analytics.

Route response shapes:
  POST /programs/{id}/slots               → ProgramDayResponse  (the slot; id at root)
  POST /program-slots/{slot_id}/exercises → ProgramResponse     (full program)
  PATCH /program-day-exercises/{pde_id}   → ProgramResponse     (full program)
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from app.models.enums import BlockKind
from app.services import auth as auth_service

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _sign_in(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    sub: str,
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


def _all_exercises(program_resp: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten all exercises from all days in a ProgramResponse."""
    return [ex for day in program_resp.get("days", []) for ex in day.get("exercises", [])]


async def _add_slot(
    client: AsyncClient, headers: dict[str, str], program_id: str, *, name: str
) -> str:
    """Create a training slot and return its id.

    POST /programs/{id}/slots returns a ProgramDayResponse with ``id`` at root.
    """
    resp = await client.post(
        f"/v1/programs/{program_id}/slots", headers=headers, json={"name": name}
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


# ---------------------------------------------------------------------------
# Tests: create / read / update block_kind on slot exercises
# ---------------------------------------------------------------------------


async def test_program_day_exercise_defaults_to_working(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Back-compat: omitting block_kind on create gives 'working'."""
    headers = await _sign_in(client, monkeypatch, sub="pde-default-bk")
    exercise_id = await _create_exercise(client, headers, name="Squat")

    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})
    ).json()
    slot_id = await _add_slot(client, headers, prog["id"], name="Day A")

    resp = await client.post(
        f"/v1/program-slots/{slot_id}/exercises",
        headers=headers,
        json={"exercise_id": exercise_id, "target_sets": 3, "target_reps_low": 5},
    )
    assert resp.status_code == 201, resp.text
    exercises = _all_exercises(resp.json())
    assert len(exercises) == 1
    ex = exercises[0]
    assert ex["block_kind"] == BlockKind.working.value
    assert ex["block_label"] is None


async def test_program_day_exercise_create_with_cooldown(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicitly setting block_kind='cooldown' is stored and returned."""
    headers = await _sign_in(client, monkeypatch, sub="pde-cooldown-create")
    exercise_id = await _create_exercise(client, headers, name="Stretch")

    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})
    ).json()
    slot_id = await _add_slot(client, headers, prog["id"], name="Day A")

    resp = await client.post(
        f"/v1/program-slots/{slot_id}/exercises",
        headers=headers,
        json={
            "exercise_id": exercise_id,
            "target_sets": 1,
            "block_kind": "cooldown",
            "block_label": "Cool-down",
        },
    )
    assert resp.status_code == 201, resp.text
    exercises = _all_exercises(resp.json())
    assert len(exercises) == 1
    ex = exercises[0]
    assert ex["block_kind"] == BlockKind.cooldown.value
    assert ex["block_label"] == "Cool-down"


async def test_program_day_exercise_create_with_warmup(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicitly setting block_kind='warmup' is stored and returned."""
    headers = await _sign_in(client, monkeypatch, sub="pde-warmup-create")
    exercise_id = await _create_exercise(client, headers, name="Band Pull-Apart")

    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})
    ).json()
    slot_id = await _add_slot(client, headers, prog["id"], name="Day A")

    resp = await client.post(
        f"/v1/program-slots/{slot_id}/exercises",
        headers=headers,
        json={
            "exercise_id": exercise_id,
            "target_sets": 2,
            "block_kind": "warmup",
        },
    )
    assert resp.status_code == 201, resp.text
    exercises = _all_exercises(resp.json())
    assert exercises[0]["block_kind"] == BlockKind.warmup.value


async def test_program_day_exercise_update_block_kind(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PATCH can change block_kind on an existing slot exercise."""
    headers = await _sign_in(client, monkeypatch, sub="pde-update-bk")
    exercise_id = await _create_exercise(client, headers, name="Foam Roll")

    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})
    ).json()
    slot_id = await _add_slot(client, headers, prog["id"], name="Day A")

    create_resp = await client.post(
        f"/v1/program-slots/{slot_id}/exercises",
        headers=headers,
        json={"exercise_id": exercise_id, "target_sets": 1},
    )
    assert create_resp.status_code == 201, create_resp.text
    exercises = _all_exercises(create_resp.json())
    pde_id = exercises[0]["id"]
    assert exercises[0]["block_kind"] == "working"

    patch_resp = await client.patch(
        f"/v1/program-day-exercises/{pde_id}",
        headers=headers,
        json={"block_kind": "cooldown", "block_label": "Recovery"},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    patched_exercises = _all_exercises(patch_resp.json())
    patched = next(e for e in patched_exercises if e["id"] == pde_id)
    assert patched["block_kind"] == BlockKind.cooldown.value
    assert patched["block_label"] == "Recovery"


# ---------------------------------------------------------------------------
# Tests: session materialization carries block_kind / block_label
# ---------------------------------------------------------------------------


async def test_start_session_copies_cooldown_block_kind(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Core behavior: a program slot exercise with block_kind='cooldown' produces
    a workout_exercise with block_kind='cooldown' in the materialized session."""
    headers = await _sign_in(client, monkeypatch, sub="mat-cooldown-bk")
    working_ex = await _create_exercise(client, headers, name="Bench Press")
    cooldown_ex = await _create_exercise(client, headers, name="Pec Stretch")

    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})
    ).json()
    slot_id = await _add_slot(client, headers, prog["id"], name="Push")

    # Add a working exercise
    await client.post(
        f"/v1/program-slots/{slot_id}/exercises",
        headers=headers,
        json={"exercise_id": working_ex, "target_sets": 3, "target_reps_low": 8},
    )
    # Add a cooldown exercise with a label
    await client.post(
        f"/v1/program-slots/{slot_id}/exercises",
        headers=headers,
        json={
            "exercise_id": cooldown_ex,
            "target_sets": 1,
            "block_kind": "cooldown",
            "block_label": "Pec cool-down",
        },
    )

    act = await client.post(f"/v1/programs/{prog['id']}/activate", headers=headers)
    assert act.status_code == 200, act.text

    session_resp = await client.post(f"/v1/programs/{prog['id']}/start-session", headers=headers)
    assert session_resp.status_code == 201, session_resp.text
    session = session_resp.json()

    exercises = session["workout_exercises"]
    assert len(exercises) == 2

    working_we = next(e for e in exercises if e["exercise_id"] == working_ex)
    cooldown_we = next(e for e in exercises if e["exercise_id"] == cooldown_ex)

    assert working_we["block_kind"] == BlockKind.working.value
    assert working_we["block_label"] is None

    assert cooldown_we["block_kind"] == BlockKind.cooldown.value
    assert cooldown_we["block_label"] == "Pec cool-down"


async def test_start_session_copies_warmup_block_kind(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A program slot exercise with block_kind='warmup' produces a workout_exercise
    with block_kind='warmup' in the materialized session."""
    headers = await _sign_in(client, monkeypatch, sub="mat-warmup-bk")
    warmup_ex = await _create_exercise(client, headers, name="Face Pull")
    working_ex = await _create_exercise(client, headers, name="OHP")

    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "P2", "goal": "general"})
    ).json()
    slot_id = await _add_slot(client, headers, prog["id"], name="Press Day")

    await client.post(
        f"/v1/program-slots/{slot_id}/exercises",
        headers=headers,
        json={"exercise_id": warmup_ex, "target_sets": 2, "block_kind": "warmup"},
    )
    await client.post(
        f"/v1/program-slots/{slot_id}/exercises",
        headers=headers,
        json={"exercise_id": working_ex, "target_sets": 4, "target_reps_low": 5},
    )

    act = await client.post(f"/v1/programs/{prog['id']}/activate", headers=headers)
    assert act.status_code == 200, act.text

    session_resp = await client.post(f"/v1/programs/{prog['id']}/start-session", headers=headers)
    assert session_resp.status_code == 201, session_resp.text
    exercises = session_resp.json()["workout_exercises"]
    assert len(exercises) == 2

    warmup_we = next(e for e in exercises if e["exercise_id"] == warmup_ex)
    working_we = next(e for e in exercises if e["exercise_id"] == working_ex)

    assert warmup_we["block_kind"] == BlockKind.warmup.value
    assert working_we["block_kind"] == BlockKind.working.value


async def test_start_session_working_block_kind_default(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When no block_kind is specified on the slot exercise, the materialized
    workout_exercise defaults to 'working' (back-compat)."""
    headers = await _sign_in(client, monkeypatch, sub="mat-default-bk")
    exercise_id = await _create_exercise(client, headers, name="Deadlift")

    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "P3", "goal": "strength"})
    ).json()
    slot_id = await _add_slot(client, headers, prog["id"], name="Pull")

    await client.post(
        f"/v1/program-slots/{slot_id}/exercises",
        headers=headers,
        json={"exercise_id": exercise_id, "target_sets": 3, "target_reps_low": 5},
    )

    act = await client.post(f"/v1/programs/{prog['id']}/activate", headers=headers)
    assert act.status_code == 200, act.text

    session_resp = await client.post(f"/v1/programs/{prog['id']}/start-session", headers=headers)
    assert session_resp.status_code == 201, session_resp.text
    exercises = session_resp.json()["workout_exercises"]
    assert len(exercises) == 1
    assert exercises[0]["block_kind"] == BlockKind.working.value
