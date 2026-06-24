"""Integration tests for the periodization mode field and per-lift reactive
deload (the still-supported periodization behaviors after the flexible
microcycle/mesocycle model removed week-based scheduling)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db import get_sessionmaker
from app.models.analytics_insight import AnalyticsInsight
from app.models.exercise_progression import ExerciseProgression
from app.models.workout import WorkoutSession
from app.services import auth as auth_service
from tests._scheduling_helpers import seed_scheduled_for_program


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
                "periodization_mode": periodization_mode,
                "auto_deload_on_stall": auto_deload_on_stall,
            },
        )
    ).json()
    slot = (
        await client.post(
            f"/v1/programs/{program['id']}/slots",
            headers=headers,
            json={"name": "Day 1"},
        )
    ).json()
    await client.post(
        f"/v1/program-slots/{slot['id']}/exercises",
        headers=headers,
        json={
            "exercise_id": exercise_id,
            "target_sets": 3,
            "target_reps_low": target_reps_low,
            "progression_strategy": progression,
        },
    )
    await client.post(f"/v1/programs/{program['id']}/activate", headers=headers)
    return str(program["id"])


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
        json={"name": "Blk", "goal": "general"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["periodization_mode"] == "block"
    assert body["auto_deload_on_stall"] is True


async def test_flip_periodization_mode_persists(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="flip-mode")
    program = (
        await client.post("/v1/programs", headers=headers, json={"name": "Flip", "goal": "general"})
    ).json()
    patch = await client.patch(
        f"/v1/programs/{program['id']}",
        headers=headers,
        json={"periodization_mode": "continuous"},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["periodization_mode"] == "continuous"


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
        periodization_mode="continuous",
        auto_deload_on_stall=True,
    )
    # Seed planned sessions starting in the past so the 6 finished sessions land
    # in the stagnation lookback window.
    start = date.today() - timedelta(weeks=10)
    await seed_scheduled_for_program(program_id, count=6, start=start)

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
