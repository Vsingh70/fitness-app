from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.db import get_sessionmaker
from app.models.scheduled_workout import ScheduledWorkout
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


def _make_program_payload(days_per_week: int = 4, weeks: int = 4) -> dict[str, Any]:
    return {
        "name": "Builder Test",
        "description": "Test",
        "goal": "hypertrophy",
        "weeks": weeks,
        "days_per_week": days_per_week,
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

    listed = await client.get("/v1/programs", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1


# ---------------------------------------------------------------------------
# Day + exercise + edit
# ---------------------------------------------------------------------------


async def test_add_day_then_exercise_then_patch(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed_exercises()
    headers = await _sign_in(client, monkeypatch)
    program = (
        await client.post("/v1/programs", headers=headers, json=_make_program_payload())
    ).json()
    program_id = program["id"]

    day_resp = await client.post(
        f"/v1/programs/{program_id}/days",
        headers=headers,
        json={"name": "Push"},
    )
    assert day_resp.status_code == 201
    day = day_resp.json()
    assert day["day_index"] == 0

    # Need a real exercise id.
    ex_list = (await client.get("/v1/exercises?limit=1", headers=headers)).json()
    exercise_id = ex_list["items"][0]["id"]

    add_ex = await client.post(
        f"/v1/program-days/{day['id']}/exercises",
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
    """Create program -> day -> exercise; return the pde id."""
    program = (
        await client.post("/v1/programs", headers=headers, json=_make_program_payload())
    ).json()
    day = (
        await client.post(
            f"/v1/programs/{program['id']}/days",
            headers=headers,
            json={"name": "Push"},
        )
    ).json()
    ex_list = (await client.get("/v1/exercises?limit=1", headers=headers)).json()
    add_ex = await client.post(
        f"/v1/program-days/{day['id']}/exercises",
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
    day = (
        await client.post(
            f"/v1/programs/{program['id']}/days", headers=headers, json={"name": "Push"}
        )
    ).json()
    ex_list = (await client.get("/v1/exercises?limit=1", headers=headers)).json()
    for body in (
        {"target_reps_high": 10},  # high without low
        {"target_reps_low": 10, "target_reps_high": 6},  # inverted range
    ):
        response = await client.post(
            f"/v1/program-days/{day['id']}/exercises",
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
# Activate
# ---------------------------------------------------------------------------


async def _create_4day_program_with_days(client: AsyncClient, headers: dict[str, str]) -> str:
    program = (
        await client.post(
            "/v1/programs",
            headers=headers,
            json={
                "name": "Activatable",
                "goal": "general",
                "weeks": 4,
                "days_per_week": 4,
            },
        )
    ).json()
    for name in ["Push A", "Pull A", "Push B", "Pull B"]:
        await client.post(
            f"/v1/programs/{program['id']}/days",
            headers=headers,
            json={"name": name},
        )
    return program["id"]


async def test_activate_generates_expected_schedule(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    program_id = await _create_4day_program_with_days(client, headers)

    response = await client.post(
        f"/v1/programs/{program_id}/activate",
        headers=headers,
        json={"start_date": "2026-06-01", "weekday_offset": 0, "skip_existing": True},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["scheduled_count"] == 4 * 4
    assert body["program"]["is_active"] is True

    sm = get_sessionmaker()
    async with sm() as session:
        rows = (
            (
                await session.execute(
                    select(ScheduledWorkout)
                    .where(ScheduledWorkout.program_id == program_id)
                    .order_by(ScheduledWorkout.scheduled_for)
                )
            )
            .scalars()
            .all()
        )
    assert len(rows) == 16
    # First row: 2026-06-01 is a Monday; weekday_offset=0 keeps it on Monday.
    assert rows[0].scheduled_for == date(2026, 6, 1)
    # Day 4 is Thursday of week 1.
    assert rows[3].scheduled_for == date(2026, 6, 4)
    # Day 5 (day_index 0 of week 2) is the following Monday.
    assert rows[4].scheduled_for == date(2026, 6, 8)
    # Mesocycle weeks increment.
    assert rows[0].mesocycle_week == 1
    assert rows[7].mesocycle_week == 2


async def test_activate_with_weekday_offset_anchors_first_day(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    program_id = await _create_4day_program_with_days(client, headers)

    # 2026-06-01 is Mon; offset=2 (Wed) should anchor on 2026-06-03.
    response = await client.post(
        f"/v1/programs/{program_id}/activate",
        headers=headers,
        json={"start_date": "2026-06-01", "weekday_offset": 2, "skip_existing": True},
    )
    assert response.status_code == 200

    sm = get_sessionmaker()
    async with sm() as session:
        first = (
            await session.execute(
                select(ScheduledWorkout)
                .where(ScheduledWorkout.program_id == program_id)
                .order_by(ScheduledWorkout.scheduled_for)
                .limit(1)
            )
        ).scalar_one()
    assert first.scheduled_for == date(2026, 6, 3)


async def test_reactivate_skips_prior_planned_workouts(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    first_id = await _create_4day_program_with_days(client, headers)
    second_id = await _create_4day_program_with_days(client, headers)

    # Activate first using a future date so all its workouts count as future/planned.
    future = (date.today() + timedelta(days=7)).isoformat()
    await client.post(
        f"/v1/programs/{first_id}/activate",
        headers=headers,
        json={"start_date": future, "weekday_offset": 0, "skip_existing": True},
    )
    # Activate second: old future planned ones should flip to skipped.
    response = await client.post(
        f"/v1/programs/{second_id}/activate",
        headers=headers,
        json={"start_date": future, "weekday_offset": 0, "skip_existing": True},
    )
    body = response.json()
    assert body["skipped_count"] == 16  # all 16 of first's planned workouts skipped

    sm = get_sessionmaker()
    async with sm() as session:
        active_count = (
            await session.execute(
                select(func.count())
                .select_from(ScheduledWorkout)
                .where(
                    ScheduledWorkout.program_id == first_id,
                    ScheduledWorkout.status == "skipped",
                )
            )
        ).scalar_one()
    assert active_count == 16


async def test_activate_requires_full_day_count(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    program = (
        await client.post(
            "/v1/programs",
            headers=headers,
            json={
                "name": "Incomplete",
                "goal": "general",
                "weeks": 2,
                "days_per_week": 4,
            },
        )
    ).json()
    # Only add 2 days; activation should refuse with 409.
    for name in ["A", "B"]:
        await client.post(
            f"/v1/programs/{program['id']}/days",
            headers=headers,
            json={"name": name},
        )

    response = await client.post(
        f"/v1/programs/{program['id']}/activate",
        headers=headers,
        json={"start_date": "2026-06-01", "weekday_offset": 0, "skip_existing": True},
    )
    assert response.status_code == 409


async def test_deactivate_clears_is_active(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    program_id = await _create_4day_program_with_days(client, headers)

    future = (date.today() + timedelta(days=7)).isoformat()
    await client.post(
        f"/v1/programs/{program_id}/activate",
        headers=headers,
        json={"start_date": future, "weekday_offset": 0, "skip_existing": True},
    )
    deactivate = await client.post(f"/v1/programs/{program_id}/deactivate", headers=headers)
    assert deactivate.status_code == 200
    assert deactivate.json()["is_active"] is False


# ---------------------------------------------------------------------------
# Single-active partial unique index sanity check
# ---------------------------------------------------------------------------


async def test_only_one_active_at_a_time_per_user(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    a = await _create_4day_program_with_days(client, headers)
    b = await _create_4day_program_with_days(client, headers)
    future = (date.today() + timedelta(days=14)).isoformat()
    await client.post(
        f"/v1/programs/{a}/activate",
        headers=headers,
        json={"start_date": future, "weekday_offset": 0, "skip_existing": True},
    )
    await client.post(
        f"/v1/programs/{b}/activate",
        headers=headers,
        json={"start_date": future, "weekday_offset": 0, "skip_existing": True},
    )
    listed = (await client.get("/v1/programs", headers=headers)).json()
    actives = [item for item in listed["items"] if item["is_active"]]
    assert len(actives) == 1
    assert actives[0]["id"] == b


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
