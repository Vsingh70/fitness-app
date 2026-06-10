"""Foods endpoints resolving + caching through FatSecret.

FatSecret HTTP is mocked at the client-function level (the service calls
``fs.search_foods`` / ``fs.get_food`` / ``fs.lookup_barcode``); the real API is
never called. Covers: search miss caches into foods + food_servings, cache hit
skips the callout, barcode maps a GTIN to a food with servings, barcode
unknown-method/miss falls through to OFF then 404, and every returned food
exposes at least one serving with a resolved gram weight.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.clients import fatsecret as fs
from app.clients import openfoodfacts as off
from app.db import get_sessionmaker
from app.services import auth as auth_service


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "fs-sub"
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _chicken_food() -> fs.FatSecretFood:
    return fs.FatSecretFood(
        food_id="33691",
        name="Grilled Chicken Breast",
        brand="Generic",
        kcal_per_100g=Decimal("165.00"),
        protein_g_per_100g=Decimal("31.00"),
        carbs_g_per_100g=Decimal("0.00"),
        fat_g_per_100g=Decimal("3.60"),
        fiber_g_per_100g=Decimal("0.00"),
        servings=[
            fs.FatSecretServing(
                description="100 g",
                metric_amount=Decimal("100.000"),
                metric_unit="g",
                grams=Decimal("100.000"),
                is_default=True,
            ),
            fs.FatSecretServing(
                description="1 cup, diced",
                metric_amount=Decimal("140.000"),
                metric_unit="g",
                grams=Decimal("140.000"),
                is_default=False,
            ),
        ],
    )


async def _count_servings_for(external_id: str) -> int:
    sm = get_sessionmaker()
    async with sm() as db:
        result = await db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM food_servings fserv
                JOIN foods f ON f.id = fserv.food_id
                WHERE f.external_id = :ext AND f.source = 'fatsecret'
                """
            ),
            {"ext": external_id},
        )
        return int(result.scalar_one())


# Search --------------------------------------------------------------------


async def test_search_miss_calls_fatsecret_and_caches(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)

    search_calls: list[str] = []
    detail_calls: list[str] = []

    async def fake_search(query: str, **kw: Any) -> list[fs.FatSecretSearchHit]:
        search_calls.append(query)
        return [fs.FatSecretSearchHit(food_id="33691", name="Grilled Chicken Breast", brand=None)]

    async def fake_get(food_id: str) -> fs.FatSecretFood:
        detail_calls.append(food_id)
        return _chicken_food()

    monkeypatch.setattr(fs, "search_foods", fake_search)
    monkeypatch.setattr(fs, "get_food", fake_get)

    response = await client.get("/v1/foods/search?q=grilled%20chicken", headers=headers)
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    names = [i["name"] for i in items]
    assert "Grilled Chicken Breast" in names
    assert search_calls == ["grilled chicken"]
    assert detail_calls == ["33691"]

    # Cached into foods + food_servings.
    assert await _count_servings_for("33691") == 2
    food = next(i for i in items if i["name"] == "Grilled Chicken Breast")
    assert food["source"] == "fatsecret"
    # At least one serving with a resolved gram weight.
    assert any(s["grams"] is not None for s in food["servings"])
    default = next(s for s in food["servings"] if s["is_default"])
    assert Decimal(default["grams"]) == Decimal("100.000")


async def test_search_cache_hit_does_not_call_fatsecret(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)

    calls: list[str] = []

    async def fake_search(query: str, **kw: Any) -> list[fs.FatSecretSearchHit]:
        calls.append(query)
        return [fs.FatSecretSearchHit(food_id="500", name="Cached Cod Fillet", brand=None)]

    async def fake_get(food_id: str) -> fs.FatSecretFood:
        return fs.FatSecretFood(
            food_id="500",
            name="Cached Cod Fillet",
            brand=None,
            kcal_per_100g=Decimal("82.00"),
            protein_g_per_100g=Decimal("18.00"),
            carbs_g_per_100g=Decimal("0.00"),
            fat_g_per_100g=Decimal("0.70"),
            fiber_g_per_100g=Decimal("0.00"),
            servings=[
                fs.FatSecretServing(
                    description="100 g",
                    metric_amount=Decimal("100.000"),
                    metric_unit="g",
                    grams=Decimal("100.000"),
                    is_default=True,
                ),
            ]
            * 6,  # >= FATSECRET_TOPUP_THRESHOLD distinct names not needed; see below
        )

    # Seed enough fatsecret rows so the cache is no longer "thin" for this query.
    sm = get_sessionmaker()
    async with sm() as db:
        for n in range(6):
            await db.execute(
                text(
                    """
                    INSERT INTO foods
                      (id, source, external_id, name, kcal_per_100g, payload,
                       created_at, updated_at)
                    VALUES
                      (gen_random_uuid(), 'fatsecret', :ext, :name, 82, '{}'::jsonb,
                       NOW(), NOW())
                    """
                ),
                {"ext": f"cod-{n}", "name": f"Cached Cod Fillet {n}"},
            )
        await db.commit()

    monkeypatch.setattr(fs, "search_foods", fake_search)
    monkeypatch.setattr(fs, "get_food", fake_get)

    response = await client.get("/v1/foods/search?q=cached%20cod%20fillet", headers=headers)
    assert response.status_code == 200, response.text
    # Cache was warm enough; FatSecret was not called.
    assert calls == []


# Detail by id --------------------------------------------------------------


async def test_get_food_by_id_returns_servings(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)

    async def fake_search(query: str, **kw: Any) -> list[fs.FatSecretSearchHit]:
        return [fs.FatSecretSearchHit(food_id="33691", name="Grilled Chicken Breast", brand=None)]

    async def fake_get(food_id: str) -> fs.FatSecretFood:
        return _chicken_food()

    monkeypatch.setattr(fs, "search_foods", fake_search)
    monkeypatch.setattr(fs, "get_food", fake_get)

    search = await client.get("/v1/foods/search?q=grilled%20chicken", headers=headers)
    food_id = next(i["id"] for i in search.json()["items"] if i["name"] == "Grilled Chicken Breast")

    detail = await client.get(f"/v1/foods/{food_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert len(body["servings"]) == 2
    assert any(s["grams"] is not None for s in body["servings"])


# Barcode -------------------------------------------------------------------


async def test_barcode_resolves_via_fatsecret_with_servings(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)

    barcode_calls: list[str] = []

    async def fake_lookup(barcode: str) -> fs.FatSecretFood:
        barcode_calls.append(barcode)
        return _chicken_food()

    async def fake_off(barcode: str, **kw: Any) -> Any:
        raise AssertionError("OFF should not be called when FatSecret resolves")

    monkeypatch.setattr(fs, "lookup_barcode", fake_lookup)
    monkeypatch.setattr(off, "fetch_product", fake_off)

    response = await client.get("/v1/foods/barcode/0012345678905", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "fatsecret"
    assert body["name"] == "Grilled Chicken Breast"
    assert any(s["grams"] is not None for s in body["servings"])
    assert barcode_calls == ["0012345678905"]


async def test_barcode_unknown_method_falls_through_to_off(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)

    off_calls: list[str] = []

    async def fake_lookup(barcode: str) -> fs.FatSecretFood:
        # Barcode method not on our tier → caller falls through to OFF.
        raise fs.FatSecretMethodNotAllowedError("unknown method")

    async def fake_off(barcode: str, **kw: Any) -> off.OffProduct:
        off_calls.append(barcode)
        return off.OffProduct(
            barcode=barcode,
            name="OFF Granola Bar",
            brand="ACME",
            serving_size_g=Decimal("40.00"),
            serving_label="1 bar",
            kcal_per_100g=Decimal("420.00"),
            protein_g_per_100g=Decimal("8.00"),
            carbs_g_per_100g=Decimal("60.00"),
            fat_g_per_100g=Decimal("16.00"),
            fiber_g_per_100g=Decimal("5.00"),
        )

    monkeypatch.setattr(fs, "lookup_barcode", fake_lookup)
    monkeypatch.setattr(off, "fetch_product", fake_off)

    response = await client.get("/v1/foods/barcode/0099999999999", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "OFF Granola Bar"
    assert response.json()["source"] == "off"
    assert off_calls == ["0099999999999"]


async def test_barcode_both_miss_returns_404(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)

    async def fake_lookup(barcode: str) -> fs.FatSecretFood:
        raise fs.FatSecretNotFoundError(barcode)

    async def fake_off(barcode: str, **kw: Any) -> Any:
        raise off.OffNotFoundError(barcode)

    monkeypatch.setattr(fs, "lookup_barcode", fake_lookup)
    monkeypatch.setattr(off, "fetch_product", fake_off)

    response = await client.get("/v1/foods/barcode/0000000000000", headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["message"] == "not_found"


async def test_search_degrades_silently_when_fatsecret_unconfigured(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)

    # Seed a local custom row so search still returns something.
    me = (await client.get("/v1/me", headers=headers)).json()
    sm = get_sessionmaker()
    async with sm() as db:
        await db.execute(
            text(
                """
                INSERT INTO foods
                  (id, source, external_id, name, kcal_per_100g, owner_id, payload,
                   created_at, updated_at)
                VALUES
                  (gen_random_uuid(), 'custom', NULL, 'Homemade Lentil Dal', 120,
                   :owner, '{}'::jsonb, NOW(), NOW())
                """
            ),
            {"owner": me["id"]},
        )
        await db.commit()

    async def fake_search(query: str, **kw: Any) -> list[fs.FatSecretSearchHit]:
        raise fs.FatSecretConfigError("not configured")

    monkeypatch.setattr(fs, "search_foods", fake_search)

    response = await client.get("/v1/foods/search?q=lentil%20dal", headers=headers)
    assert response.status_code == 200, response.text
    names = [i["name"] for i in response.json()["items"]]
    assert "Homemade Lentil Dal" in names
