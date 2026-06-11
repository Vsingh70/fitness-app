"""Meals, meal items, daily summary, meal plans, body metrics, targets."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.db import get_sessionmaker
from app.services import auth as auth_service


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "meal-sub"
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
    fiber: str | None = "1",
) -> str:
    sm = get_sessionmaker()
    async with sm() as db:
        row = (
            await db.execute(
                text(
                    """
                    INSERT INTO foods (id, source, name, kcal_per_100g, protein_g_per_100g,
                                       carbs_g_per_100g, fat_g_per_100g, fiber_g_per_100g,
                                       payload, created_at, updated_at)
                    VALUES (gen_random_uuid(), 'usda', :name, :kcal, :protein,
                            :carbs, :fat, :fiber, '{}'::jsonb, NOW(), NOW())
                    RETURNING id
                    """
                ),
                {
                    "name": name,
                    "kcal": Decimal(kcal),
                    "protein": Decimal(protein),
                    "carbs": Decimal(carbs),
                    "fat": Decimal(fat),
                    "fiber": Decimal(fiber) if fiber else None,
                },
            )
        ).first()
        await db.commit()
        return str(row[0])


# ---------------------------------------------------------------------------
# Macro denormalization
# ---------------------------------------------------------------------------


async def test_add_item_denormalizes_macros_proportionally(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    food_id = await _seed_food("Chicken", kcal="165", protein="31", carbs="0", fat="3.6")

    meal = (
        await client.post(
            "/v1/meals",
            headers=headers,
            json={"eaten_at": "2026-05-25T12:00:00Z", "meal_type": "lunch"},
        )
    ).json()
    item = (
        await client.post(
            f"/v1/meals/{meal['id']}/items",
            headers=headers,
            json={"food_id": food_id, "grams": "200"},
        )
    ).json()
    # 200g * (165/100) = 330 kcal
    assert Decimal(item["kcal"]) == Decimal("330.00")
    # 200g * (31/100) = 62 g protein
    assert Decimal(item["protein_g"]) == Decimal("62.00")
    assert Decimal(item["fat_g"]) == Decimal("7.20")


async def test_update_item_grams_scales_macros(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    food_id = await _seed_food("Chicken", kcal="165", protein="31", carbs="0", fat="3.6")
    meal = (
        await client.post(
            "/v1/meals",
            headers=headers,
            json={"eaten_at": "2026-05-25T12:00:00Z", "meal_type": "lunch"},
        )
    ).json()
    item = (
        await client.post(
            f"/v1/meals/{meal['id']}/items",
            headers=headers,
            json={"food_id": food_id, "grams": "100"},
        )
    ).json()
    # Patch to 250g -> 2.5x macros (412.5 kcal).
    updated = (
        await client.patch(
            f"/v1/meal-items/{item['id']}",
            headers=headers,
            json={"grams": "250"},
        )
    ).json()
    assert Decimal(updated["grams"]) == Decimal("250.00")
    assert Decimal(updated["kcal"]) == Decimal("412.50")
    assert Decimal(updated["protein_g"]) == Decimal("77.50")


async def test_update_item_changes_food_repulls_macros(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    food_a = await _seed_food("A", kcal="100", protein="10", carbs="5", fat="2")
    food_b = await _seed_food("B", kcal="400", protein="20", carbs="50", fat="10")
    meal = (
        await client.post(
            "/v1/meals",
            headers=headers,
            json={"eaten_at": "2026-05-25T12:00:00Z", "meal_type": "lunch"},
        )
    ).json()
    item = (
        await client.post(
            f"/v1/meals/{meal['id']}/items",
            headers=headers,
            json={"food_id": food_a, "grams": "100"},
        )
    ).json()
    swapped = (
        await client.patch(
            f"/v1/meal-items/{item['id']}",
            headers=headers,
            json={"food_id": food_b},
        )
    ).json()
    # food_b at 100g: 400 kcal.
    assert swapped["food_id"] == food_b
    assert Decimal(swapped["kcal"]) == Decimal("400.00")


async def test_editing_food_row_does_not_rewrite_item_history(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The denormalized item macros must stay fixed even if the food row is
    later edited (custom food owner case).
    """
    headers = await _sign_in(client, monkeypatch)
    custom = (
        await client.post(
            "/v1/foods",
            headers=headers,
            json={
                "name": "Mystery Bar",
                "kcal_per_100g": "300",
                "protein_g_per_100g": "20",
                "carbs_g_per_100g": "40",
                "fat_g_per_100g": "10",
            },
        )
    ).json()
    meal = (
        await client.post(
            "/v1/meals",
            headers=headers,
            json={"eaten_at": "2026-05-25T12:00:00Z", "meal_type": "snack"},
        )
    ).json()
    item = (
        await client.post(
            f"/v1/meals/{meal['id']}/items",
            headers=headers,
            json={"food_id": custom["id"], "grams": "50"},
        )
    ).json()
    original_kcal = item["kcal"]

    # User later realizes the bar has more kcal than thought; updates the food.
    await client.patch(
        f"/v1/foods/{custom['id']}",
        headers=headers,
        json={"kcal_per_100g": "500"},
    )

    refreshed = (await client.get(f"/v1/meals/{meal['id']}", headers=headers)).json()
    assert refreshed["items"][0]["kcal"] == original_kcal


# ---------------------------------------------------------------------------
# Soft delete + daily summary
# ---------------------------------------------------------------------------


async def test_meal_soft_delete_removes_from_list_and_totals(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    food_id = await _seed_food("A", kcal="100", protein="10", carbs="5", fat="2")
    meal = (
        await client.post(
            "/v1/meals",
            headers=headers,
            json={"eaten_at": "2026-05-25T12:00:00Z", "meal_type": "lunch"},
        )
    ).json()
    await client.post(
        f"/v1/meals/{meal['id']}/items",
        headers=headers,
        json={"food_id": food_id, "grams": "200"},
    )
    deletion = await client.delete(f"/v1/meals/{meal['id']}", headers=headers)
    assert deletion.status_code == 204

    lst = (await client.get("/v1/meals", headers=headers)).json()
    assert all(m["id"] != meal["id"] for m in lst["items"])

    day = (
        await client.get(
            "/v1/nutrition/day?date=2026-05-25",
            headers=headers,
        )
    ).json()
    assert Decimal(day["totals"]["kcal"]) == Decimal("0.00")


async def test_daily_summary_aggregates_across_meals(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    chicken = await _seed_food("Chicken", kcal="165", protein="31", carbs="0", fat="3.6")
    rice = await _seed_food("Rice", kcal="130", protein="2.7", carbs="28", fat="0.3")

    breakfast = (
        await client.post(
            "/v1/meals",
            headers=headers,
            json={"eaten_at": "2026-05-25T08:00:00Z", "meal_type": "breakfast"},
        )
    ).json()
    await client.post(
        f"/v1/meals/{breakfast['id']}/items",
        headers=headers,
        json={"food_id": chicken, "grams": "100"},
    )
    lunch = (
        await client.post(
            "/v1/meals",
            headers=headers,
            json={"eaten_at": "2026-05-25T13:00:00Z", "meal_type": "lunch"},
        )
    ).json()
    await client.post(
        f"/v1/meals/{lunch['id']}/items",
        headers=headers,
        json={"food_id": rice, "grams": "200"},
    )

    day = (await client.get("/v1/nutrition/day?date=2026-05-25", headers=headers)).json()
    # 165 + 260 = 425 kcal; 31 + 5.4 = 36.4 protein
    assert Decimal(day["totals"]["kcal"]) == Decimal("425.00")
    assert Decimal(day["totals"]["protein_g"]) == Decimal("36.40")
    assert len(day["per_meal"]) == 2


# ---------------------------------------------------------------------------
# Meal plans
# ---------------------------------------------------------------------------


async def test_only_one_plan_active_at_a_time(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    payload_a = {
        "name": "Cut",
        "target_kcal": "2000",
        "target_protein_g": "180",
        "target_carbs_g": "150",
        "target_fat_g": "70",
    }
    payload_b = dict(payload_a, name="Bulk", target_kcal="3000")
    plan_a = (await client.post("/v1/meal-plans", headers=headers, json=payload_a)).json()
    plan_b = (await client.post("/v1/meal-plans", headers=headers, json=payload_b)).json()

    await client.post(f"/v1/meal-plans/{plan_a['id']}/activate", headers=headers)
    await client.post(f"/v1/meal-plans/{plan_b['id']}/activate", headers=headers)

    plans = (await client.get("/v1/meal-plans", headers=headers)).json()["items"]
    actives = [p for p in plans if p["is_active"]]
    assert len(actives) == 1
    assert actives[0]["id"] == plan_b["id"]


async def test_active_plan_with_progress(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    plan = (
        await client.post(
            "/v1/meal-plans",
            headers=headers,
            json={
                "name": "Cut",
                "target_kcal": "2000",
                "target_protein_g": "180",
                "target_carbs_g": "150",
                "target_fat_g": "70",
            },
        )
    ).json()
    await client.post(f"/v1/meal-plans/{plan['id']}/activate", headers=headers)

    food = await _seed_food("A", kcal="200", protein="20", carbs="20", fat="5")
    today = datetime.now(tz=UTC).date()
    meal = (
        await client.post(
            "/v1/meals",
            headers=headers,
            json={"eaten_at": f"{today}T12:00:00Z", "meal_type": "lunch"},
        )
    ).json()
    await client.post(
        f"/v1/meals/{meal['id']}/items",
        headers=headers,
        json={"food_id": food, "grams": "500"},
    )
    response = await client.get("/v1/meal-plans/active", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert Decimal(body["consumed"]["kcal"]) == Decimal("1000.00")
    assert Decimal(body["remaining"]["kcal"]) == Decimal("1000.00")


# ---------------------------------------------------------------------------
# Targets derivation
# ---------------------------------------------------------------------------


async def test_targets_uses_active_plan_when_set(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    plan = (
        await client.post(
            "/v1/meal-plans",
            headers=headers,
            json={
                "name": "Cut",
                "target_kcal": "2200",
                "target_protein_g": "180",
                "target_carbs_g": "200",
                "target_fat_g": "70",
            },
        )
    ).json()
    await client.post(f"/v1/meal-plans/{plan['id']}/activate", headers=headers)
    response = await client.get("/v1/nutrition/targets", headers=headers)
    body = response.json()
    assert Decimal(body["target_kcal"]) == Decimal("2200.00")
    assert Decimal(body["target_protein_g"]) == Decimal("180.00")


async def test_targets_derives_from_mifflin_when_no_plan(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    # Profile setup: 30y old male, 180 cm, 80 kg.
    await client.patch(
        "/v1/me",
        headers=headers,
        json={
            "sex_at_birth": "male",
            "birthdate": "1996-01-01",
            "height_cm": "180",
        },
    )
    await client.post(
        "/v1/body-metrics",
        headers=headers,
        json={"recorded_at": datetime.now(tz=UTC).isoformat(), "weight_kg": "80"},
    )
    response = await client.get("/v1/nutrition/targets", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    # Mifflin-St Jeor: BMR = 10*80 + 6.25*180 - 5*age + 5
    # age depends on test date; just check structural shape and plausible range.
    assert Decimal(body["target_kcal"]) > Decimal("1500")
    assert Decimal(body["target_kcal"]) < Decimal("4000")
    # Protein = 2.0 g/kg * 80 = 160 g
    assert Decimal(body["target_protein_g"]) == Decimal("160.00")


async def test_targets_409_when_profile_incomplete(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    response = await client.get("/v1/nutrition/targets", headers=headers)
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Body metrics
# ---------------------------------------------------------------------------


async def test_body_metric_log_and_list(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    now = datetime.now(tz=UTC)
    create = await client.post(
        "/v1/body-metrics",
        headers=headers,
        json={
            "recorded_at": now.isoformat(),
            "weight_kg": "80.50",
            "body_fat_pct": "18.5",
        },
    )
    assert create.status_code == 201
    later = await client.post(
        "/v1/body-metrics",
        headers=headers,
        json={"recorded_at": (now + timedelta(days=1)).isoformat(), "weight_kg": "80.20"},
    )
    assert later.status_code == 201
    listing = await client.get("/v1/body-metrics", headers=headers)
    items = listing.json()["items"]
    # Newest first.
    assert Decimal(items[0]["weight_kg"]) == Decimal("80.20")


# ---------------------------------------------------------------------------
# Foods archive path (now meal_items exists)
# ---------------------------------------------------------------------------


async def test_food_with_meal_items_archives_on_delete(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The foods delete path should now archive (not hard-delete) because the
    food is referenced by a meal_item.
    """
    headers = await _sign_in(client, monkeypatch)
    food = (
        await client.post(
            "/v1/foods",
            headers=headers,
            json={"name": "Referenced Food", "kcal_per_100g": "100"},
        )
    ).json()
    meal = (
        await client.post(
            "/v1/meals",
            headers=headers,
            json={"eaten_at": "2026-05-25T12:00:00Z", "meal_type": "lunch"},
        )
    ).json()
    await client.post(
        f"/v1/meals/{meal['id']}/items",
        headers=headers,
        json={"food_id": food["id"], "grams": "100"},
    )
    delete = await client.delete(f"/v1/foods/{food['id']}", headers=headers)
    assert delete.status_code == 204

    # The food should still exist in the DB but no longer surface in search.
    search = await client.get("/v1/foods/search?q=referenced%20food", headers=headers)
    names = [i["name"] for i in search.json()["items"]]
    assert "Referenced Food" not in names

    # Direct DB check: archived_at is set.
    sm = get_sessionmaker()
    async with sm() as db:
        row = (
            await db.execute(
                text("SELECT archived_at FROM foods WHERE id = :id"),
                {"id": food["id"]},
            )
        ).first()
    assert row is not None and row[0] is not None
