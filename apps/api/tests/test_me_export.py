"""Full account data export bundle (GET /v1/me/export)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db import get_sessionmaker
from app.models.body_metric import BodyMetric
from app.models.enums import (
    Equipment,
    MealType,
    MovementPattern,
    Muscle,
    ProgramGoal,
    ProgramSource,
    ProgressionStrategy,
    SetType,
    TrackingType,
)
from app.models.exercise import Exercise
from app.models.food import Food
from app.models.meal import Meal, MealItem
from app.models.program import Program, ProgramDay, ProgramDayExercise
from app.models.user import User
from app.models.workout import WorkoutExercise, WorkoutSession, WorkoutSet
from app.schemas.export import EXPORT_SCHEMA_VERSION
from app.services import auth as auth_service


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "export-sub"
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _seed_full_dataset(sub: str) -> dict[str, str]:
    """Seed one row in every table the export bundle covers, owned by the
    signed-in user identified by `sub`. Returns string ids for assertions."""
    sm = get_sessionmaker()
    async with sm() as db:
        user = (await db.execute(select(User).where(User.apple_sub == sub))).scalar_one()

        # Shared FK targets (not exported directly but required for rows).
        exercise = Exercise(
            name="Back Squat",
            slug="back-squat-export",
            primary_muscle=Muscle.quads,
            secondary_muscles=[Muscle.glutes],
            equipment=Equipment.barbell,
            movement_pattern=MovementPattern.squat,
            tracking_type=TrackingType.weight_reps,
        )
        food = Food(
            source="custom",
            name="Oats",
            kcal_per_100g=Decimal("389"),
            protein_g_per_100g=Decimal("16.9"),
            carbs_g_per_100g=Decimal("66.3"),
            fat_g_per_100g=Decimal("6.9"),
            fiber_g_per_100g=Decimal("10.6"),
            payload={},
        )
        db.add_all([exercise, food])
        await db.flush()

        # Workout session + exercise + set.
        ws = WorkoutSession(
            user_id=user.id,
            name="Leg Day",
            started_at=datetime(2026, 5, 1, 17, 0, tzinfo=UTC),
        )
        db.add(ws)
        await db.flush()
        we = WorkoutExercise(workout_session_id=ws.id, exercise_id=exercise.id, position=0)
        db.add(we)
        await db.flush()
        wset = WorkoutSet(
            workout_exercise_id=we.id,
            set_index=0,
            set_type=SetType.working,
            weight_kg=Decimal("100.00"),
            reps=5,
        )
        db.add(wset)

        # Meal + item.
        meal = Meal(
            user_id=user.id,
            eaten_at=datetime(2026, 5, 1, 8, 0, tzinfo=UTC),
            meal_type=MealType.breakfast,
        )
        db.add(meal)
        await db.flush()
        meal_item = MealItem(
            meal_id=meal.id,
            food_id=food.id,
            grams=Decimal("80.00"),
            kcal=Decimal("311.20"),
        )
        db.add(meal_item)

        # Body metric.
        bm = BodyMetric(
            user_id=user.id,
            recorded_at=datetime(2026, 5, 1, 7, 0, tzinfo=UTC),
            weight_kg=Decimal("82.50"),
        )
        db.add(bm)

        # Program + day + exercise.
        program = Program(
            owner_id=user.id,
            name="My Program",
            goal=ProgramGoal.hypertrophy,
            microcycle_length=3,
            mesocycle_length_microcycles=4,
            source=ProgramSource.manual,
        )
        db.add(program)
        await db.flush()
        pday = ProgramDay(program_id=program.id, slot_index=0, name="Day A")
        db.add(pday)
        await db.flush()
        pde = ProgramDayExercise(
            program_day_id=pday.id,
            exercise_id=exercise.id,
            position=0,
            target_sets=3,
            target_reps_low=8,
            target_reps_high=12,
            progression_strategy=ProgressionStrategy.double_progression,
        )
        db.add(pde)

        await db.commit()

        return {
            "user_id": str(user.id),
            "session_id": str(ws.id),
            "workout_exercise_id": str(we.id),
            "set_id": str(wset.id),
            "meal_id": str(meal.id),
            "meal_item_id": str(meal_item.id),
            "body_metric_id": str(bm.id),
            "program_id": str(program.id),
            "program_day_id": str(pday.id),
            "program_day_exercise_id": str(pde.id),
        }


async def test_export_bundle_contains_seeded_rows_from_each_table(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    ids = await _seed_full_dataset("export-sub")

    response = await client.get("/v1/me/export", headers=headers)
    assert response.status_code == 200, response.text
    bundle = response.json()

    # Schema version present and matches the current format.
    assert bundle["schema_version"] == EXPORT_SCHEMA_VERSION
    assert "exported_at" in bundle

    # User block.
    assert bundle["user"]["id"] == ids["user_id"]

    # Workout sessions + exercises + sets.
    assert len(bundle["workout_sessions"]) == 1
    session = bundle["workout_sessions"][0]
    assert session["id"] == ids["session_id"]
    assert len(session["workout_exercises"]) == 1
    assert session["workout_exercises"][0]["id"] == ids["workout_exercise_id"]
    assert len(session["workout_exercises"][0]["sets"]) == 1
    assert session["workout_exercises"][0]["sets"][0]["id"] == ids["set_id"]

    # Meals + items.
    assert len(bundle["meals"]) == 1
    assert bundle["meals"][0]["id"] == ids["meal_id"]
    assert len(bundle["meals"][0]["items"]) == 1
    assert bundle["meals"][0]["items"][0]["id"] == ids["meal_item_id"]

    # Body metrics.
    assert len(bundle["body_metrics"]) == 1
    assert bundle["body_metrics"][0]["id"] == ids["body_metric_id"]

    # Programs + days + exercises.
    assert len(bundle["programs"]) == 1
    program = bundle["programs"][0]
    assert program["id"] == ids["program_id"]
    assert len(program["days"]) == 1
    assert program["days"][0]["id"] == ids["program_day_id"]
    assert len(program["days"][0]["exercises"]) == 1
    assert program["days"][0]["exercises"][0]["id"] == ids["program_day_exercise_id"]


async def test_export_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/v1/me/export")
    assert response.status_code == 401


async def test_export_is_scoped_to_current_user(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # User A seeds a full dataset.
    headers_a = await _sign_in(client, monkeypatch, sub="export-owner")
    await _seed_full_dataset("export-owner")

    # User B (different sub) gets an empty bundle but a valid envelope.
    headers_b = await _sign_in(client, monkeypatch, sub="export-other")
    response = await client.get("/v1/me/export", headers=headers_b)
    assert response.status_code == 200, response.text
    bundle = response.json()
    assert bundle["schema_version"] == EXPORT_SCHEMA_VERSION
    assert bundle["workout_sessions"] == []
    assert bundle["meals"] == []
    assert bundle["body_metrics"] == []
    assert bundle["programs"] == []

    # And user A still sees their own data.
    response_a = await client.get("/v1/me/export", headers=headers_a)
    assert response_a.status_code == 200
    assert len(response_a.json()["workout_sessions"]) == 1

    # Sanity: ids parse as UUIDs.
    UUID(bundle["user"]["id"])
