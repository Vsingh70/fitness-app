"""Meal-plan logging + flexible tracking (06.06).

Covers mark-complete materialization + idempotency, delete today/forever,
serving-size edits, swap, multi-unit flexible tracking, and grams-only
back-compat.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.db import get_sessionmaker
from app.services import auth as auth_service


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "log-sub"
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


async def _plan_with_meal(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    food_id: str,
    amount: str = "200",
    unit: str = "g",
    planned_time: str | None = None,
    meal_name: str = "Lunch",
) -> dict[str, Any]:
    """Create + activate a daily plan with one meal/one item; return the plan."""
    meal: dict[str, Any] = {
        "name": meal_name,
        "slot_index": 0,
        "items": [{"food_id": food_id, "amount": amount, "unit": unit}],
    }
    if planned_time is not None:
        meal["planned_time"] = planned_time
    plan = (
        await client.post(
            "/v1/meal-plans",
            headers=headers,
            json={
                "name": "Daily",
                "plan_kind": "daily_repeating",
                "content_mode": "meals_only",
                "day_templates": [{"day_role": "every_day", "meals": [meal]}],
            },
        )
    ).json()
    await client.post(f"/v1/meal-plans/{plan['id']}/activate", headers=headers)
    return plan


# ---------------------------------------------------------------------------
# Mark complete
# ---------------------------------------------------------------------------


async def test_complete_materializes_items_and_links_source(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    food = await _seed_food("Chicken", kcal="165", protein="31", carbs="0", fat="3.6")
    plan = await _plan_with_meal(
        client, headers, food_id=food, amount="200", unit="g", planned_time="12:30:00"
    )
    plan_meal = plan["day_templates"][0]["meals"][0]

    res = await client.post(
        f"/v1/meal-plans/{plan['id']}/meals/{plan_meal['id']}/complete?date=2026-06-10",
        headers=headers,
    )
    assert res.status_code == 201, res.text
    logged = res.json()
    assert logged["source_plan_meal_id"] == plan_meal["id"]
    assert logged["source_plan_date"] == "2026-06-10"
    # planned_time on the date -> eaten_at.
    assert logged["eaten_at"].startswith("2026-06-10T12:30:00")
    assert len(logged["items"]) == 1
    item = logged["items"][0]
    assert Decimal(item["grams"]) == Decimal("200.00")
    # 200g chicken = 330 kcal.
    assert Decimal(item["kcal"]) == Decimal("330.00")
    assert Decimal(item["protein_g"]) == Decimal("62.00")


async def test_recomplete_same_slot_date_is_idempotent(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    food = await _seed_food("Food")
    plan = await _plan_with_meal(client, headers, food_id=food)
    plan_meal = plan["day_templates"][0]["meals"][0]
    url = f"/v1/meal-plans/{plan['id']}/meals/{plan_meal['id']}/complete?date=2026-06-10"

    first = (await client.post(url, headers=headers)).json()
    second = (await client.post(url, headers=headers)).json()
    assert first["id"] == second["id"]

    meals = (await client.get("/v1/meals", headers=headers)).json()["items"]
    completions = [m for m in meals if m["source_plan_meal_id"] == plan_meal["id"]]
    assert len(completions) == 1


async def test_complete_appears_in_day_adherence(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    food = await _seed_food("Food")
    plan = await _plan_with_meal(client, headers, food_id=food)
    plan_meal = plan["day_templates"][0]["meals"][0]

    # The plan meal has no planned_time, so completion stamps eaten_at=now() (UTC).
    # The /nutrition/day window here uses the default tz_offset_minutes=0 (a UTC
    # day), so query today (UTC) for the completion to land inside the window
    # regardless of wall-clock date.
    target = datetime.now(tz=UTC).date().isoformat()

    day = (await client.get(f"/v1/nutrition/day?date={target}", headers=headers)).json()
    assert day["adherence"]["planned_meals"] == 1
    assert day["adherence"]["completed_meals"] == 0
    assert day["tracking_mode"] == "macros_and_calories"

    await client.post(
        f"/v1/meal-plans/{plan['id']}/meals/{plan_meal['id']}/complete?date={target}",
        headers=headers,
    )
    day = (await client.get(f"/v1/nutrition/day?date={target}", headers=headers)).json()
    assert day["adherence"]["completed_meals"] == 1
    assert plan_meal["id"] in day["adherence"]["completed_plan_meal_ids"]


# ---------------------------------------------------------------------------
# Delete scope
# ---------------------------------------------------------------------------


async def test_delete_today_soft_deletes_only_logged_meal(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    food = await _seed_food("Food")
    plan = await _plan_with_meal(client, headers, food_id=food)
    plan_meal = plan["day_templates"][0]["meals"][0]
    logged = (
        await client.post(
            f"/v1/meal-plans/{plan['id']}/meals/{plan_meal['id']}/complete?date=2026-06-10",
            headers=headers,
        )
    ).json()

    res = await client.delete(f"/v1/meals/{logged['id']}?scope=today", headers=headers)
    assert res.status_code == 204

    # Logged meal gone from the list.
    meals = (await client.get("/v1/meals", headers=headers)).json()["items"]
    assert all(m["id"] != logged["id"] for m in meals)
    # Plan template still has the meal -> future resolution still includes it.
    refreshed = (await client.get(f"/v1/meal-plans/{plan['id']}", headers=headers)).json()
    meal_ids = [m["id"] for m in refreshed["day_templates"][0]["meals"]]
    assert plan_meal["id"] in meal_ids


async def test_delete_forever_removes_plan_template_meal(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    food = await _seed_food("Food")
    plan = await _plan_with_meal(client, headers, food_id=food)
    plan_meal = plan["day_templates"][0]["meals"][0]
    logged = (
        await client.post(
            f"/v1/meal-plans/{plan['id']}/meals/{plan_meal['id']}/complete?date=2026-06-10",
            headers=headers,
        )
    ).json()

    res = await client.delete(f"/v1/meals/{logged['id']}?scope=forever", headers=headers)
    assert res.status_code == 204

    refreshed = (await client.get(f"/v1/meal-plans/{plan['id']}", headers=headers)).json()
    meal_ids = [m["id"] for m in refreshed["day_templates"][0]["meals"]]
    assert plan_meal["id"] not in meal_ids
    # And future resolution no longer surfaces it.
    resolved = (
        await client.get(f"/v1/meal-plans/{plan['id']}/day?date=2026-06-17", headers=headers)
    ).json()
    if resolved["template"] is not None:
        assert all(m["id"] != plan_meal["id"] for m in resolved["template"]["meals"])


async def test_delete_forever_on_non_plan_meal_behaves_like_today(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    food = await _seed_food("Food")
    meal = (
        await client.post(
            "/v1/meals",
            headers=headers,
            json={"eaten_at": "2026-06-10T12:00:00Z", "meal_type": "lunch"},
        )
    ).json()
    await client.post(
        f"/v1/meals/{meal['id']}/items",
        headers=headers,
        json={"food_id": food, "grams": "100"},
    )
    res = await client.delete(f"/v1/meals/{meal['id']}?scope=forever", headers=headers)
    assert res.status_code == 204
    meals = (await client.get("/v1/meals", headers=headers)).json()["items"]
    assert all(m["id"] != meal["id"] for m in meals)


# ---------------------------------------------------------------------------
# Serving-size edit re-denormalizes
# ---------------------------------------------------------------------------


async def test_serving_edit_redenormalizes_macros(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    food = await _seed_food("Oats", kcal="380", protein="13", carbs="67", fat="7")
    serving = await _seed_serving(food, description="1 cup (80 g)", grams="80")
    meal = (
        await client.post(
            "/v1/meals",
            headers=headers,
            json={"eaten_at": "2026-06-10T08:00:00Z", "meal_type": "breakfast"},
        )
    ).json()
    item = (
        await client.post(
            f"/v1/meals/{meal['id']}/items",
            headers=headers,
            json={"food_id": food, "amount": "1", "unit": "serving", "serving_id": serving},
        )
    ).json()
    # 1 cup = 80 g -> 304 kcal.
    assert Decimal(item["grams"]) == Decimal("80.00")
    assert Decimal(item["kcal"]) == Decimal("304.00")

    # Bump to 2 cups -> 160 g -> 608 kcal.
    updated = (
        await client.patch(
            f"/v1/meal-items/{item['id']}",
            headers=headers,
            json={"amount": "2"},
        )
    ).json()
    assert Decimal(updated["grams"]) == Decimal("160.00")
    assert Decimal(updated["kcal"]) == Decimal("608.00")
    assert updated["unit"] == "serving"


# ---------------------------------------------------------------------------
# Swap
# ---------------------------------------------------------------------------


async def test_swap_from_plan_meal_replaces_items(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    food_a = await _seed_food("A", kcal="100")
    food_b = await _seed_food("B", kcal="400")
    plan = await _plan_with_meal(client, headers, food_id=food_b, amount="100", unit="g")
    plan_meal = plan["day_templates"][0]["meals"][0]

    meal = (
        await client.post(
            "/v1/meals",
            headers=headers,
            json={"eaten_at": "2026-06-10T12:00:00Z", "meal_type": "lunch"},
        )
    ).json()
    await client.post(
        f"/v1/meals/{meal['id']}/items",
        headers=headers,
        json={"food_id": food_a, "grams": "100"},
    )
    swapped = (
        await client.post(
            f"/v1/meals/{meal['id']}/swap",
            headers=headers,
            json={"plan_meal_id": plan_meal["id"]},
        )
    ).json()
    assert len(swapped["items"]) == 1
    assert swapped["items"][0]["food_id"] == food_b
    assert Decimal(swapped["items"][0]["kcal"]) == Decimal("400.00")


async def test_swap_from_items_recomputes_totals(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    food_a = await _seed_food("A", kcal="100")
    food_b = await _seed_food("B", kcal="200")
    meal = (
        await client.post(
            "/v1/meals",
            headers=headers,
            json={"eaten_at": "2026-06-10T12:00:00Z", "meal_type": "lunch"},
        )
    ).json()
    await client.post(
        f"/v1/meals/{meal['id']}/items",
        headers=headers,
        json={"food_id": food_a, "grams": "100"},
    )
    swapped = (
        await client.post(
            f"/v1/meals/{meal['id']}/swap",
            headers=headers,
            json={
                "items": [
                    {"food_id": food_a, "amount": "100", "unit": "g"},
                    {"food_id": food_b, "amount": "50", "unit": "g"},
                ]
            },
        )
    ).json()
    assert len(swapped["items"]) == 2
    # 100g A (100) + 50g B (100) = 200 kcal.
    total = sum(Decimal(i["kcal"]) for i in swapped["items"])
    assert total == Decimal("200.00")


async def test_swap_requires_exactly_one_source(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    meal = (
        await client.post(
            "/v1/meals",
            headers=headers,
            json={"eaten_at": "2026-06-10T12:00:00Z", "meal_type": "lunch"},
        )
    ).json()
    res = await client.post(f"/v1/meals/{meal['id']}/swap", headers=headers, json={})
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Flexible multi-unit tracking + grams-only back-compat
# ---------------------------------------------------------------------------


async def test_flexible_multi_unit_meal_totals_correctly(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    food = await _seed_food("Oats", kcal="380", protein="13", carbs="67", fat="7")
    serving = await _seed_serving(food, description="1 cup (80 g)", grams="80")
    meal = (
        await client.post(
            "/v1/meals",
            headers=headers,
            json={"eaten_at": "2026-06-10T08:00:00Z", "meal_type": "breakfast"},
        )
    ).json()
    # g
    await client.post(
        f"/v1/meals/{meal['id']}/items",
        headers=headers,
        json={"food_id": food, "amount": "100", "unit": "g"},
    )
    # ml (water-equiv: 250 ml == 250 g)
    await client.post(
        f"/v1/meals/{meal['id']}/items",
        headers=headers,
        json={"food_id": food, "amount": "250", "unit": "ml"},
    )
    # serving (2 * 80 g = 160 g)
    await client.post(
        f"/v1/meals/{meal['id']}/items",
        headers=headers,
        json={"food_id": food, "amount": "2", "unit": "serving", "serving_id": serving},
    )

    full = (await client.get(f"/v1/meals/{meal['id']}", headers=headers)).json()
    by_unit = {i["unit"]: i for i in full["items"]}
    assert Decimal(by_unit["g"]["grams"]) == Decimal("100.00")
    assert Decimal(by_unit["ml"]["grams"]) == Decimal("250.00")
    assert Decimal(by_unit["serving"]["grams"]) == Decimal("160.00")
    # Total grams = 510 g -> 510 * 3.8 = 1938 kcal.
    total_kcal = sum(Decimal(i["kcal"]) for i in full["items"])
    assert total_kcal == Decimal("1938.00")

    day = (await client.get("/v1/nutrition/day?date=2026-06-10", headers=headers)).json()
    assert Decimal(day["totals"]["kcal"]) == Decimal("1938.00")


async def test_grams_only_item_create_still_works(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    food = await _seed_food("Chicken", kcal="165", protein="31", carbs="0", fat="3.6")
    meal = (
        await client.post(
            "/v1/meals",
            headers=headers,
            json={"eaten_at": "2026-06-10T12:00:00Z", "meal_type": "lunch"},
        )
    ).json()
    item = (
        await client.post(
            f"/v1/meals/{meal['id']}/items",
            headers=headers,
            json={"food_id": food, "grams": "200"},
        )
    ).json()
    assert Decimal(item["grams"]) == Decimal("200.00")
    assert Decimal(item["amount"]) == Decimal("200.000")
    assert item["unit"] == "g"
    assert Decimal(item["kcal"]) == Decimal("330.00")
