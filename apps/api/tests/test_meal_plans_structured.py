"""Structured meal plans: kinds, content/tracking modes, resolution, totals."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.db import get_sessionmaker
from app.services import auth as auth_service


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "plan-sub"
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _seed_food(
    name: str,
    *,
    kcal: str = "100",
    protein: str = "10",
    carbs: str = "5",
    fat: str = "2",
) -> str:
    sm = get_sessionmaker()
    async with sm() as db:
        row = (
            await db.execute(
                text(
                    """
                    INSERT INTO foods (id, source, name, kcal_per_100g, protein_g_per_100g,
                                       carbs_g_per_100g, fat_g_per_100g, payload,
                                       created_at, updated_at)
                    VALUES (gen_random_uuid(), 'usda', :name, :kcal, :protein,
                            :carbs, :fat, '{}'::jsonb, NOW(), NOW())
                    RETURNING id
                    """
                ),
                {
                    "name": name,
                    "kcal": Decimal(kcal),
                    "protein": Decimal(protein),
                    "carbs": Decimal(carbs),
                    "fat": Decimal(fat),
                },
            )
        ).first()
        await db.commit()
        return str(row[0])


async def _seed_serving(food_id: str, *, description: str, grams: str) -> str:
    sm = get_sessionmaker()
    async with sm() as db:
        row = (
            await db.execute(
                text(
                    """
                    INSERT INTO food_servings (id, food_id, description, metric_unit,
                                               grams, is_default, created_at)
                    VALUES (gen_random_uuid(), :food_id, :description, 'g',
                            :grams, true, NOW())
                    RETURNING id
                    """
                ),
                {"food_id": food_id, "description": description, "grams": Decimal(grams)},
            )
        ).first()
        await db.commit()
        return str(row[0])


async def _seed_scheduled_workout(client_headers_sub: str, *, scheduled_for: date) -> None:
    """Insert a ScheduledWorkout for the signed-in user on a date."""
    sm = get_sessionmaker()
    async with sm() as db:
        await db.execute(
            text(
                """
                INSERT INTO scheduled_workouts
                    (id, user_id, scheduled_for, status, is_deload, created_at, updated_at)
                SELECT gen_random_uuid(), u.id, :scheduled_for, 'planned', false, NOW(), NOW()
                FROM users u
                WHERE u.apple_sub = :sub
                """
            ),
            {"scheduled_for": scheduled_for, "sub": client_headers_sub},
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Totals roll-up + target derivation
# ---------------------------------------------------------------------------


async def test_item_meal_day_totals_roll_up(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    chicken = await _seed_food("Chicken", kcal="165", protein="31", carbs="0", fat="3.6")
    rice = await _seed_food("Rice", kcal="130", protein="2.7", carbs="28", fat="0.3")

    plan = (
        await client.post(
            "/v1/meal-plans",
            headers=headers,
            json={
                "name": "Daily",
                "plan_kind": "daily_repeating",
                "content_mode": "meals_only",
                "tracking_mode": "macros_and_calories",
                "day_templates": [
                    {
                        "day_role": "every_day",
                        "meals": [
                            {
                                "name": "Lunch",
                                "slot_index": 0,
                                "items": [
                                    {"food_id": chicken, "amount": "200", "unit": "g"},
                                    {"food_id": rice, "amount": "150", "unit": "g"},
                                ],
                            }
                        ],
                    }
                ],
            },
        )
    ).json()

    day = plan["day_templates"][0]
    meal = day["meals"][0]
    # 200g chicken = 330 kcal; 150g rice = 195 kcal -> 525.
    assert Decimal(meal["totals"]["kcal"]) == Decimal("525.00")
    assert Decimal(day["totals"]["kcal"]) == Decimal("525.00")
    # meals_only -> effective targets derive from summed foods.
    assert Decimal(day["effective_targets"]["target_kcal"]) == Decimal("525.00")
    # protein: 200*0.31=62 + 150*0.027=4.05 -> 66.05
    assert Decimal(day["effective_targets"]["target_protein_g"]) == Decimal("66.05")


async def test_per_day_target_override_beats_summed_meals(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    food = await _seed_food("Food", kcal="100", protein="10", carbs="5", fat="2")
    plan = (
        await client.post(
            "/v1/meal-plans",
            headers=headers,
            json={
                "name": "Both",
                "plan_kind": "daily_repeating",
                "content_mode": "targets_and_meals",
                "day_templates": [
                    {
                        "day_role": "every_day",
                        "target_kcal": "2500",
                        "meals": [
                            {
                                "name": "Snack",
                                "items": [{"food_id": food, "amount": "100", "unit": "g"}],
                            }
                        ],
                    }
                ],
            },
        )
    ).json()
    day = plan["day_templates"][0]
    # Override wins over the 100-kcal summed total.
    assert Decimal(day["effective_targets"]["target_kcal"]) == Decimal("2500.00")
    assert Decimal(day["totals"]["kcal"]) == Decimal("100.00")


# ---------------------------------------------------------------------------
# Amount -> grams conversions
# ---------------------------------------------------------------------------


async def test_serving_ml_g_conversion_and_denormalization(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    food = await _seed_food("Oats", kcal="380", protein="13", carbs="67", fat="7")
    serving = await _seed_serving(food, description="1 cup (80 g)", grams="80")

    plan = (
        await client.post(
            "/v1/meal-plans",
            headers=headers,
            json={
                "name": "Conversions",
                "plan_kind": "daily_repeating",
                "content_mode": "meals_only",
                "day_templates": [
                    {
                        "day_role": "every_day",
                        "meals": [
                            {
                                "name": "Breakfast",
                                "items": [
                                    {"food_id": food, "amount": "100", "unit": "g"},
                                    {"food_id": food, "amount": "250", "unit": "ml"},
                                    {
                                        "food_id": food,
                                        "amount": "2",
                                        "unit": "serving",
                                        "serving_id": serving,
                                    },
                                ],
                            }
                        ],
                    }
                ],
            },
        )
    ).json()
    items = plan["day_templates"][0]["meals"][0]["items"]
    by_unit = {i["unit"]: i for i in items}
    # g: 100 g -> 380 kcal.
    assert Decimal(by_unit["g"]["grams"]) == Decimal("100.00")
    assert Decimal(by_unit["g"]["kcal"]) == Decimal("380.00")
    # ml: 250 ml == 250 g (water-equiv) -> 950 kcal.
    assert Decimal(by_unit["ml"]["grams"]) == Decimal("250.00")
    assert Decimal(by_unit["ml"]["kcal"]) == Decimal("950.00")
    # serving: 2 * 80 g = 160 g -> 608 kcal.
    assert Decimal(by_unit["serving"]["grams"]) == Decimal("160.00")
    assert Decimal(by_unit["serving"]["kcal"]) == Decimal("608.00")


# ---------------------------------------------------------------------------
# training_rest resolution: manual + synced
# ---------------------------------------------------------------------------


async def _training_rest_plan(
    client: AsyncClient, headers: dict[str, str], **extra: Any
) -> dict[str, Any]:
    return (
        await client.post(
            "/v1/meal-plans",
            headers=headers,
            json={
                "name": "T/R",
                "plan_kind": "training_rest",
                "content_mode": "targets_only",
                "day_templates": [
                    {"day_role": "training", "target_kcal": "3000"},
                    {"day_role": "rest", "target_kcal": "2200"},
                ],
                **extra,
            },
        )
    ).json()


async def test_training_rest_manual_resolves_by_training_dows(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    # Monday=0 and Wednesday=2 are training days.
    plan = await _training_rest_plan(client, headers, training_dows=[0, 2])

    # 2026-06-08 is a Monday -> training.
    monday = "2026-06-08"
    wednesday = "2026-06-10"
    tuesday = "2026-06-09"

    res_mon = (
        await client.get(f"/v1/meal-plans/{plan['id']}/day?date={monday}", headers=headers)
    ).json()
    assert res_mon["day_role"] == "training"
    assert res_mon["is_training_day"] is True
    assert Decimal(res_mon["effective_targets"]["target_kcal"]) == Decimal("3000.00")

    res_tue = (
        await client.get(f"/v1/meal-plans/{plan['id']}/day?date={tuesday}", headers=headers)
    ).json()
    assert res_tue["day_role"] == "rest"
    assert res_tue["is_training_day"] is False
    assert Decimal(res_tue["effective_targets"]["target_kcal"]) == Decimal("2200.00")

    res_wed = (
        await client.get(f"/v1/meal-plans/{plan['id']}/day?date={wednesday}", headers=headers)
    ).json()
    assert res_wed["day_role"] == "training"


async def test_training_rest_synced_resolves_by_program_schedule(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    sub = "synced-sub"
    headers = await _sign_in(client, monkeypatch, sub=sub)
    plan = await _training_rest_plan(client, headers, synced_to_program=True)

    workout_day = date(2026, 6, 8)
    rest_day = date(2026, 6, 9)
    await _seed_scheduled_workout(sub, scheduled_for=workout_day)

    res_workout = (
        await client.get(f"/v1/meal-plans/{plan['id']}/day?date={workout_day}", headers=headers)
    ).json()
    assert res_workout["day_role"] == "training"
    assert res_workout["is_training_day"] is True

    res_rest = (
        await client.get(f"/v1/meal-plans/{plan['id']}/day?date={rest_day}", headers=headers)
    ).json()
    assert res_rest["day_role"] == "rest"
    assert res_rest["is_training_day"] is False


# ---------------------------------------------------------------------------
# weekly resolution + week reset
# ---------------------------------------------------------------------------


async def test_weekly_resolves_by_weekday(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    plan = (
        await client.post(
            "/v1/meal-plans",
            headers=headers,
            json={
                "name": "Weekly",
                "plan_kind": "weekly",
                "content_mode": "targets_only",
                "day_templates": [
                    {"day_role": f"dow_{i}", "target_kcal": str(2000 + i * 100)} for i in range(7)
                ],
            },
        )
    ).json()
    # 2026-06-08 = Monday (weekday 0) -> dow_0; 2026-06-10 = Wednesday -> dow_2.
    res_mon = (
        await client.get(f"/v1/meal-plans/{plan['id']}/day?date=2026-06-08", headers=headers)
    ).json()
    assert res_mon["day_role"] == "dow_0"
    assert Decimal(res_mon["effective_targets"]["target_kcal"]) == Decimal("2000.00")

    res_wed = (
        await client.get(f"/v1/meal-plans/{plan['id']}/day?date=2026-06-10", headers=headers)
    ).json()
    assert res_wed["day_role"] == "dow_2"
    assert Decimal(res_wed["effective_targets"]["target_kcal"]) == Decimal("2200.00")


async def test_week_resets_flips_needs_review_at_week_start(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    plan = (
        await client.post(
            "/v1/meal-plans",
            headers=headers,
            json={
                "name": "Weekly reset",
                "plan_kind": "weekly",
                "content_mode": "targets_only",
                "week_resets": True,
                "week_start_dow": 0,
                "day_templates": [
                    {"day_role": f"dow_{i}", "target_kcal": "2000"} for i in range(7)
                ],
            },
        )
    ).json()
    await client.post(f"/v1/meal-plans/{plan['id']}/activate", headers=headers)
    assert plan["needs_week_review"] is False

    # Resolve a date in a future week -> review flag should flip on.
    future = (date.today() + timedelta(days=14)).isoformat()
    await client.get(f"/v1/meal-plans/{plan['id']}/day?date={future}", headers=headers)

    refreshed = (await client.get(f"/v1/meal-plans/{plan['id']}", headers=headers)).json()
    assert refreshed["needs_week_review"] is True

    # User reviews -> clears the flag via PATCH.
    cleared = (
        await client.patch(
            f"/v1/meal-plans/{plan['id']}",
            headers=headers,
            json={"needs_week_review": False},
        )
    ).json()
    assert cleared["needs_week_review"] is False


# ---------------------------------------------------------------------------
# tracking_mode + active resolution
# ---------------------------------------------------------------------------


async def test_tracking_mode_returned_in_resolution(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    plan = (
        await client.post(
            "/v1/meal-plans",
            headers=headers,
            json={
                "name": "Cals",
                "plan_kind": "daily_repeating",
                "content_mode": "targets_only",
                "tracking_mode": "calories_only",
                "target_kcal": "2000",
                "day_templates": [{"day_role": "every_day"}],
            },
        )
    ).json()
    assert plan["tracking_mode"] == "calories_only"
    res = (
        await client.get(f"/v1/meal-plans/{plan['id']}/day?date=2026-06-08", headers=headers)
    ).json()
    assert res["tracking_mode"] == "calories_only"
    # Plan-default target flows through to the resolved day.
    assert Decimal(res["effective_targets"]["target_kcal"]) == Decimal("2000.00")


async def test_activate_enforces_single_active(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    a = (
        await client.post(
            "/v1/meal-plans",
            headers=headers,
            json={"name": "A", "content_mode": "targets_only", "target_kcal": "2000"},
        )
    ).json()
    b = (
        await client.post(
            "/v1/meal-plans",
            headers=headers,
            json={"name": "B", "content_mode": "targets_only", "target_kcal": "2500"},
        )
    ).json()
    await client.post(f"/v1/meal-plans/{a['id']}/activate", headers=headers)
    await client.post(f"/v1/meal-plans/{b['id']}/activate", headers=headers)

    plans = (await client.get("/v1/meal-plans", headers=headers)).json()["items"]
    actives = [p for p in plans if p["is_active"]]
    assert len(actives) == 1
    assert actives[0]["id"] == b["id"]


async def test_active_endpoint_returns_resolved_day(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    plan = (
        await client.post(
            "/v1/meal-plans",
            headers=headers,
            json={
                "name": "Active",
                "plan_kind": "daily_repeating",
                "content_mode": "targets_only",
                "target_kcal": "2000",
                "target_protein_g": "180",
                "target_carbs_g": "150",
                "target_fat_g": "70",
                "day_templates": [{"day_role": "every_day"}],
            },
        )
    ).json()
    await client.post(f"/v1/meal-plans/{plan['id']}/activate", headers=headers)

    res = (await client.get("/v1/meal-plans/active?date=2026-06-08", headers=headers)).json()
    assert res["resolved_day"]["day_role"] == "every_day"
    assert Decimal(res["resolved_day"]["effective_targets"]["target_kcal"]) == Decimal("2000.00")
    assert Decimal(res["remaining"]["kcal"]) == Decimal("2000.00")


# ---------------------------------------------------------------------------
# Nested edits
# ---------------------------------------------------------------------------


async def test_nested_add_meal_and_item_recomputes_totals(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    food = await _seed_food("Food", kcal="100", protein="10", carbs="5", fat="2")
    plan = (
        await client.post(
            "/v1/meal-plans",
            headers=headers,
            json={
                "name": "Editable",
                "plan_kind": "daily_repeating",
                "content_mode": "meals_only",
                "day_templates": [{"day_role": "every_day"}],
            },
        )
    ).json()
    day_id = plan["day_templates"][0]["id"]

    after_meal = (
        await client.post(
            f"/v1/meal-plan-days/{day_id}/meals",
            headers=headers,
            json={"name": "Lunch", "items": [{"food_id": food, "amount": "200", "unit": "g"}]},
        )
    ).json()
    day = after_meal["day_templates"][0]
    assert Decimal(day["totals"]["kcal"]) == Decimal("200.00")

    item_id = day["meals"][0]["items"][0]["id"]
    after_patch = (
        await client.patch(
            f"/v1/meal-plan-items/{item_id}",
            headers=headers,
            json={"amount": "300"},
        )
    ).json()
    assert Decimal(after_patch["day_templates"][0]["totals"]["kcal"]) == Decimal("300.00")


# ---------------------------------------------------------------------------
# Deactivate
# ---------------------------------------------------------------------------


async def test_deactivate_plan(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    headers = await _sign_in(client, monkeypatch, sub="deactivate-sub")

    # Create and activate a plan.
    plan = (
        await client.post(
            "/v1/meal-plans",
            headers=headers,
            json={"name": "ToDeactivate", "content_mode": "targets_only", "target_kcal": "2000"},
        )
    ).json()
    activate_res = await client.post(f"/v1/meal-plans/{plan['id']}/activate", headers=headers)
    assert activate_res.status_code == 200
    assert activate_res.json()["is_active"] is True

    # Deactivate it.
    deactivate_res = await client.post(f"/v1/meal-plans/{plan['id']}/deactivate", headers=headers)
    assert deactivate_res.status_code == 200
    assert deactivate_res.json()["is_active"] is False

    # Deactivate again — idempotent, must still return 200 and is_active=False.
    deactivate_again = await client.post(f"/v1/meal-plans/{plan['id']}/deactivate", headers=headers)
    assert deactivate_again.status_code == 200
    assert deactivate_again.json()["is_active"] is False

    # Activating a second plan after deactivating the first still yields exactly
    # one active plan.
    second = (
        await client.post(
            "/v1/meal-plans",
            headers=headers,
            json={"name": "Second", "content_mode": "targets_only", "target_kcal": "2500"},
        )
    ).json()
    await client.post(f"/v1/meal-plans/{second['id']}/activate", headers=headers)

    plans = (await client.get("/v1/meal-plans", headers=headers)).json()["items"]
    actives = [p for p in plans if p["is_active"]]
    assert len(actives) == 1
    assert actives[0]["id"] == second["id"]
