"""Integration tests for the periodization toggle (block vs continuous)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.db import get_sessionmaker
from app.models.analytics_insight import AnalyticsInsight
from app.models.enums import ScheduledWorkoutStatus
from app.models.exercise_progression import ExerciseProgression
from app.models.scheduled_workout import ScheduledWorkout
from app.models.workout import WorkoutSession
from app.services import auth as auth_service


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _exercise_payload(name: str = "Bench (periodization)") -> dict[str, Any]:
    return {
        "name": name,
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
    periodization_mode: str = "block",
    auto_deload_on_stall: bool = True,
    progression: str = "linear",
    target_reps_low: int = 5,
) -> str:
    program = (
        await client.post(
            "/v1/programs",
            headers=headers,
            json={
                "name": "Periodization Prog",
                "goal": "strength",
                "weeks": weeks,
                "days_per_week": 1,
                "periodization_mode": periodization_mode,
                "auto_deload_on_stall": auto_deload_on_stall,
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
            "progression_strategy": progression,
        },
    )
    return str(program["id"])


async def _activate(
    client: AsyncClient,
    headers: dict[str, str],
    program_id: str,
    *,
    start_date: str = "2026-06-01",
    weekday_offset: int = 0,
) -> Any:
    response = await client.post(
        f"/v1/programs/{program_id}/activate",
        headers=headers,
        json={
            "start_date": start_date,
            "weekday_offset": weekday_offset,
            "skip_existing": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_create_program_carries_periodization_fields(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="cont-create")
    response = await client.post(
        "/v1/programs",
        headers=headers,
        json={
            "name": "Cont",
            "goal": "general",
            "weeks": 4,
            "days_per_week": 1,
            "periodization_mode": "continuous",
            "auto_deload_on_stall": False,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["periodization_mode"] == "continuous"
    assert body["auto_deload_on_stall"] is False


async def test_create_program_defaults_to_block(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="block-default")
    response = await client.post(
        "/v1/programs",
        headers=headers,
        json={"name": "Blk", "goal": "general", "weeks": 4, "days_per_week": 1},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["periodization_mode"] == "block"
    assert body["auto_deload_on_stall"] is True


async def test_continuous_activation_has_no_deloads_or_meso_framing(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="cont-activate")
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    program_id = await _create_program(
        client, headers, exercise_id=exercise["id"], weeks=4, periodization_mode="continuous"
    )
    await _activate(client, headers, program_id)
    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    assert len(scheduled) == 4
    assert all(s["is_deload"] is False for s in scheduled)
    assert all(s["mesocycle_week"] is None for s in scheduled)


async def test_mesocycle_endpoint_reports_continuous(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="cont-meso")
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    program_id = await _create_program(
        client, headers, exercise_id=exercise["id"], weeks=4, periodization_mode="continuous"
    )
    await _activate(client, headers, program_id)

    data = (await client.get(f"/v1/programs/{program_id}/mesocycle", headers=headers)).json()
    assert data["periodization_mode"] == "continuous"
    assert data["is_continuous"] is True
    assert data["current_week"] is None
    assert data["week_in_meso"] is None
    assert data["is_deload"] is False
    assert data["next_week_is_deload"] is False


async def test_continuous_calendar_auto_extends_on_finalize(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Finishing a session near the end of the rolling horizon tops the calendar
    back up; it never empties."""
    headers = await _sign_in(client, monkeypatch, sub="cont-extend")
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    # 2 weeks * 1 day = 2 scheduled rows initially. The horizon is anchored on
    # the start date so the rows are all "near today" -> the extend should fire.
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    program_id = await _create_program(
        client, headers, exercise_id=exercise["id"], weeks=2, periodization_mode="continuous"
    )
    await _activate(
        client,
        headers,
        program_id,
        start_date=monday.isoformat(),
        weekday_offset=today.weekday(),
    )

    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    initial_count = len(scheduled)
    assert initial_count == 2

    # Finish the first (today's) session.
    first = scheduled[0]
    workout = (
        await client.post(f"/v1/scheduled-workouts/{first['id']}/start", headers=headers)
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

    # The rolling calendar should now hold MORE planned future rows than before,
    # all with no deload framing.
    sm = get_sessionmaker()
    async with sm() as s:
        future_planned = (
            await s.execute(
                select(func.count())
                .select_from(ScheduledWorkout)
                .where(
                    ScheduledWorkout.program_id == UUID(program_id),
                    ScheduledWorkout.status == ScheduledWorkoutStatus.planned,
                    ScheduledWorkout.scheduled_for >= today,
                )
            )
        ).scalar_one()
        any_deload = (
            await s.execute(
                select(func.count())
                .select_from(ScheduledWorkout)
                .where(
                    ScheduledWorkout.program_id == UUID(program_id),
                    ScheduledWorkout.is_deload.is_(True),
                )
            )
        ).scalar_one()
    # 1 remaining original + 4 extension weeks added = at least 4 future planned.
    assert future_planned >= 4
    assert any_deload == 0


async def test_switch_block_to_continuous_clears_future_deloads(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="switch-b2c")
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    # Block program with deloads. Activate starting today so future rows exist.
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    program = (
        await client.post(
            "/v1/programs",
            headers=headers,
            json={
                "name": "B2C",
                "goal": "strength",
                "weeks": 8,
                "days_per_week": 1,
            },
        )
    ).json()
    await client.patch(
        f"/v1/programs/{program['id']}",
        headers=headers,
        json={"mesocycle_length_weeks": 5},
    )
    day = (
        await client.post(
            f"/v1/programs/{program['id']}/days", headers=headers, json={"name": "Day 1"}
        )
    ).json()
    await client.post(
        f"/v1/program-days/{day['id']}/exercises",
        headers=headers,
        json={
            "exercise_id": exercise["id"],
            "target_sets": 3,
            "target_reps_low": 5,
            "progression_strategy": "linear",
        },
    )
    program_id = str(program["id"])
    await _activate(
        client,
        headers,
        program_id,
        start_date=monday.isoformat(),
        weekday_offset=today.weekday(),
    )

    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    assert any(s["is_deload"] for s in scheduled), "block program should have a deload week"

    # Switch to continuous.
    patch = await client.patch(
        f"/v1/programs/{program_id}",
        headers=headers,
        json={"periodization_mode": "continuous"},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["periodization_mode"] == "continuous"

    # No FUTURE row should remain a deload, and meso framing is cleared.
    sm = get_sessionmaker()
    async with sm() as s:
        future = (
            (
                await s.execute(
                    select(ScheduledWorkout).where(
                        ScheduledWorkout.program_id == UUID(program_id),
                        ScheduledWorkout.scheduled_for >= today,
                    )
                )
            )
            .scalars()
            .all()
        )
    assert future, "expected future rows"
    assert all(r.is_deload is False for r in future)
    assert all(r.mesocycle_week is None for r in future)


async def test_stalled_lift_continuous_suggests_per_lift_deload(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stalled lift on a continuous + auto_deload_on_stall program surfaces a
    per-lift deload suggestion (scoped to that exercise); applying it deloads
    only that exercise and resets its counters."""
    headers = await _sign_in(client, monkeypatch, sub="cont-stall")
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload("Stall Bench"))
    ).json()
    program_id = await _create_program(
        client,
        headers,
        exercise_id=exercise["id"],
        weeks=2,
        periodization_mode="continuous",
        auto_deload_on_stall=True,
    )
    # Activate starting in the past so the 6+ sessions all sit before today and
    # land in the stagnation lookback window.
    start = date.today() - timedelta(weeks=10)
    monday = start - timedelta(days=start.weekday())
    await _activate(
        client,
        headers,
        program_id,
        start_date=monday.isoformat(),
        weekday_offset=monday.weekday(),
    )

    # Log 6 flat sessions at the same weight/reps -> zero slope, low variance.
    # The session's started_at defaults to today, so stamp each finished session
    # onto a distinct historical date; the stagnation regression groups by
    # started_at::date and needs >= 6 distinct dated sessions to fire.
    sm = get_sessionmaker()
    for week in range(6):
        scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
        planned = [s for s in scheduled if s["status"] == "planned"]
        assert planned, "expected a planned session"
        sw = planned[0]
        workout = (
            await client.post(f"/v1/scheduled-workouts/{sw['id']}/start", headers=headers)
        ).json()
        we_id = workout["workout_exercises"][0]["id"]
        for _ in range(3):
            await client.post(
                f"/v1/workout-exercises/{we_id}/sets",
                headers=headers,
                json={"weight_kg": "100", "reps": 5, "set_type": "working"},
            )
        await client.post(f"/v1/workout-sessions/{workout['id']}/finish", headers=headers)
        # Backdate this session to a distinct week so it counts as a separate
        # data point for the stall regression.
        session_date = date.today() - timedelta(weeks=(8 - week))
        stamp = datetime.combine(session_date, time(12, 0), tzinfo=UTC)
        async with sm() as s:
            row = (
                await s.execute(
                    select(WorkoutSession).where(WorkoutSession.id == UUID(str(workout["id"])))
                )
            ).scalar_one()
            row.started_at = stamp
            row.ended_at = stamp
            await s.commit()

    # Recompute insights and confirm a per-lift deload suggestion exists.
    recompute = await client.post("/v1/insights/recompute", headers=headers)
    assert recompute.status_code == 200, recompute.text

    insights = (
        await client.get("/v1/insights", headers=headers, params={"kind": "stagnation"})
    ).json()["items"]
    stall = [
        i
        for i in insights
        if i["payload"].get("suggested_action") == "deload_exercise"
        and i["payload"].get("exercise_id") == exercise["id"]
    ]
    assert stall, f"expected a per-lift deload suggestion, got {insights}"
    assert stall[0]["payload"]["program_id"] == program_id

    # Read the exercise progression weight before the deload.
    sm = get_sessionmaker()
    async with sm() as s:
        prog = (
            await s.execute(
                select(ExerciseProgression).where(
                    ExerciseProgression.exercise_id == UUID(exercise["id"])
                )
            )
        ).scalar_one()
        prior_weight = prog.current_top_set_weight_kg

    # Apply the per-lift deload.
    deload = await client.post(
        f"/v1/programs/{program_id}/exercises/{exercise['id']}/deload",
        headers=headers,
    )
    assert deload.status_code == 200, deload.text
    body = deload.json()
    assert body["applied"] is True
    assert body["new_weight_kg"] is not None
    assert Decimal(body["new_weight_kg"]) < (prior_weight or Decimal("0"))

    # Counters reset; only this exercise touched.
    async with sm() as s:
        prog = (
            await s.execute(
                select(ExerciseProgression).where(
                    ExerciseProgression.exercise_id == UUID(exercise["id"])
                )
            )
        ).scalar_one()
        assert prog.consecutive_failures == 0
        assert prog.consecutive_successes == 0
        assert prog.consecutive_above_range == 0
        assert prog.current_top_set_weight_kg == Decimal(body["new_weight_kg"])

    # The stagnation insight should now be dismissed (acted on).
    async with sm() as s:
        active = (
            (
                await s.execute(
                    select(AnalyticsInsight).where(
                        AnalyticsInsight.subject == exercise["slug"],
                        AnalyticsInsight.dismissed_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
    assert not active, "the per-lift suggestion should be dismissed after applying"
