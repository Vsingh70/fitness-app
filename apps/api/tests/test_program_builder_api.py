from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from app.services import auth as auth_service
from scripts.seed_exercises import seed as seed_exercises
from scripts.seed_programs import seed as seed_programs


async def _sign_in(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    sub: str = "builder-sub",
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _make_program_payload() -> dict[str, Any]:
    return {
        "name": "Builder Test",
        "description": "Test",
        "goal": "hypertrophy",
    }


# ---------------------------------------------------------------------------
# Create + read
# ---------------------------------------------------------------------------


async def test_list_mine_empty(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    headers = await _sign_in(client, monkeypatch)
    response = await client.get("/v1/programs", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": None}


async def test_create_empty_program(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    headers = await _sign_in(client, monkeypatch)
    create = await client.post("/v1/programs", headers=headers, json=_make_program_payload())
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["source"] == "manual"
    assert body["days"] == []
    # A fresh program has zero slots and a zero-length microcycle.
    assert body["microcycle_length"] == 0
    assert body["mesocycle_length_microcycles"] == 4
    # intensity_mode defaults to 'rpe' when not supplied.
    assert body["intensity_mode"] == "rpe"

    listed = await client.get("/v1/programs", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1


async def test_create_program_with_intensity_mode_round_trips(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    create = await client.post(
        "/v1/programs",
        headers=headers,
        json={**_make_program_payload(), "intensity_mode": "rir"},
    )
    assert create.status_code == 201, create.text
    assert create.json()["intensity_mode"] == "rir"


async def test_patch_program_intensity_mode_round_trips(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    program = (
        await client.post("/v1/programs", headers=headers, json=_make_program_payload())
    ).json()
    assert program["intensity_mode"] == "rpe"

    patched = await client.patch(
        f"/v1/programs/{program['id']}",
        headers=headers,
        json={"intensity_mode": "off"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["intensity_mode"] == "off"


# ---------------------------------------------------------------------------
# Slot + exercise + edit
# ---------------------------------------------------------------------------


async def test_add_slot_then_exercise_then_patch(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed_exercises()
    headers = await _sign_in(client, monkeypatch)
    program = (
        await client.post("/v1/programs", headers=headers, json=_make_program_payload())
    ).json()
    program_id = program["id"]

    slot_resp = await client.post(
        f"/v1/programs/{program_id}/slots",
        headers=headers,
        json={"name": "Push"},
    )
    assert slot_resp.status_code == 201
    slot = slot_resp.json()
    assert slot["slot_index"] == 0
    assert slot["is_rest_day"] is False

    # Need a real exercise id.
    ex_list = (await client.get("/v1/exercises?limit=1", headers=headers)).json()
    exercise_id = ex_list["items"][0]["id"]

    add_ex = await client.post(
        f"/v1/program-slots/{slot['id']}/exercises",
        headers=headers,
        json={
            "exercise_id": exercise_id,
            "target_sets": 3,
            "target_reps_low": 6,
            "target_reps_high": 10,
            "rest_seconds": 120,
            "progression_strategy": "double_progression",
        },
    )
    assert add_ex.status_code == 201
    pde = add_ex.json()["days"][0]["exercises"][0]
    pde_id = pde["id"]
    assert pde["target_sets"] == 3
    assert pde["target_reps_low"] == 6

    patched = await client.patch(
        f"/v1/program-day-exercises/{pde_id}",
        headers=headers,
        json={"target_sets": 5, "rest_seconds": 180},
    )
    assert patched.status_code == 200
    updated = patched.json()["days"][0]["exercises"][0]
    assert updated["target_sets"] == 5
    assert updated["rest_seconds"] == 180


async def test_exercise_rep_mode_create_and_patch_round_trip(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed_exercises()
    headers = await _sign_in(client, monkeypatch)
    program = (
        await client.post("/v1/programs", headers=headers, json=_make_program_payload())
    ).json()
    slot = (
        await client.post(
            f"/v1/programs/{program['id']}/slots", headers=headers, json={"name": "Push"}
        )
    ).json()
    exercise_id = (await client.get("/v1/exercises?limit=1", headers=headers)).json()["items"][0][
        "id"
    ]

    # Defaults to 'range' when not supplied.
    default_add = await client.post(
        f"/v1/program-slots/{slot['id']}/exercises",
        headers=headers,
        json={"exercise_id": exercise_id, "target_sets": 3, "target_reps_low": 8},
    )
    assert default_add.status_code == 201, default_add.text
    assert default_add.json()["days"][0]["exercises"][0]["rep_mode"] == "range"

    # Explicit 'target' on create round-trips.
    target_add = await client.post(
        f"/v1/program-slots/{slot['id']}/exercises",
        headers=headers,
        json={
            "exercise_id": exercise_id,
            "target_sets": 3,
            "target_reps_low": 12,
            "rep_mode": "target",
        },
    )
    assert target_add.status_code == 201, target_add.text
    exercises = target_add.json()["days"][0]["exercises"]
    target_ex = exercises[1]
    assert target_ex["rep_mode"] == "target"

    # PATCH flips it back to 'range'.
    patched = await client.patch(
        f"/v1/program-day-exercises/{target_ex['id']}",
        headers=headers,
        json={"rep_mode": "range"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["days"][0]["exercises"][1]["rep_mode"] == "range"


# ---------------------------------------------------------------------------
# Rep-range validation
# ---------------------------------------------------------------------------


async def _program_exercise(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    target_reps_low: int | None = 6,
    target_reps_high: int | None = 10,
) -> str:
    """Create program -> slot -> exercise; return the pde id."""
    program = (
        await client.post("/v1/programs", headers=headers, json=_make_program_payload())
    ).json()
    slot = (
        await client.post(
            f"/v1/programs/{program['id']}/slots",
            headers=headers,
            json={"name": "Push"},
        )
    ).json()
    ex_list = (await client.get("/v1/exercises?limit=1", headers=headers)).json()
    add_ex = await client.post(
        f"/v1/program-slots/{slot['id']}/exercises",
        headers=headers,
        json={
            "exercise_id": ex_list["items"][0]["id"],
            "target_sets": 3,
            "target_reps_low": target_reps_low,
            "target_reps_high": target_reps_high,
        },
    )
    assert add_ex.status_code == 201, add_ex.text
    return str(add_ex.json()["days"][0]["exercises"][0]["id"])


async def test_create_exercise_rep_high_without_low_is_422(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed_exercises()
    headers = await _sign_in(client, monkeypatch)
    program = (
        await client.post("/v1/programs", headers=headers, json=_make_program_payload())
    ).json()
    slot = (
        await client.post(
            f"/v1/programs/{program['id']}/slots", headers=headers, json={"name": "Push"}
        )
    ).json()
    ex_list = (await client.get("/v1/exercises?limit=1", headers=headers)).json()
    for body in (
        {"target_reps_high": 10},  # high without low
        {"target_reps_low": 10, "target_reps_high": 6},  # inverted range
    ):
        response = await client.post(
            f"/v1/program-slots/{slot['id']}/exercises",
            headers=headers,
            json={"exercise_id": ex_list["items"][0]["id"], "target_sets": 3, **body},
        )
        assert response.status_code == 422, response.text


async def test_patch_rep_high_below_low_is_422(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed_exercises()
    headers = await _sign_in(client, monkeypatch)
    pde_id = await _program_exercise(client, headers)
    response = await client.patch(
        f"/v1/program-day-exercises/{pde_id}",
        headers=headers,
        json={"target_reps_low": 10, "target_reps_high": 6},
    )
    assert response.status_code == 422


async def test_patch_clearing_low_while_high_remains_is_422(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed_exercises()
    headers = await _sign_in(client, monkeypatch)
    pde_id = await _program_exercise(client, headers)  # low=6, high=10
    response = await client.patch(
        f"/v1/program-day-exercises/{pde_id}",
        headers=headers,
        json={"target_reps_low": None},
    )
    assert response.status_code == 422
    # Merged-state check: patching only high below the existing low also fails.
    response = await client.patch(
        f"/v1/program-day-exercises/{pde_id}",
        headers=headers,
        json={"target_reps_high": 5},
    )
    assert response.status_code == 422


async def test_patch_valid_range_and_fixed_goal_pass(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed_exercises()
    headers = await _sign_in(client, monkeypatch)
    pde_id = await _program_exercise(client, headers)

    ranged = await client.patch(
        f"/v1/program-day-exercises/{pde_id}",
        headers=headers,
        json={"target_reps_low": 8, "target_reps_high": 12},
    )
    assert ranged.status_code == 200, ranged.text
    updated = ranged.json()["days"][0]["exercises"][0]
    assert updated["target_reps_low"] == 8
    assert updated["target_reps_high"] == 12

    # Fixed goal: clearing high while low remains is fine.
    fixed = await client.patch(
        f"/v1/program-day-exercises/{pde_id}",
        headers=headers,
        json={"target_reps_high": None},
    )
    assert fixed.status_code == 200, fixed.text
    updated = fixed.json()["days"][0]["exercises"][0]
    assert updated["target_reps_low"] == 8
    assert updated["target_reps_high"] is None


# ---------------------------------------------------------------------------
# Copy + edit chain (smoke)
# ---------------------------------------------------------------------------


async def test_copy_then_edit_exercise(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed_exercises()
    await seed_programs()
    headers = await _sign_in(client, monkeypatch)

    copy = (
        await client.post("/v1/program-templates/starting-strength-3day/copy", headers=headers)
    ).json()
    pde_id = copy["days"][0]["exercises"][0]["id"]
    patch = await client.patch(
        f"/v1/program-day-exercises/{pde_id}",
        headers=headers,
        json={"target_sets": 7},
    )
    assert patch.status_code == 200
    updated = patch.json()["days"][0]["exercises"][0]
    assert updated["target_sets"] == 7
