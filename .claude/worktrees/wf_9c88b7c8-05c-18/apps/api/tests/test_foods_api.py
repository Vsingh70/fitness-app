"""Foods: search ranking, barcode caching + OFF fallback, custom CRUD."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.clients import openfoodfacts as off
from app.db import get_sessionmaker
from app.services import auth as auth_service


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "food-sub"
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _seed_food(
    source: str,
    name: str,
    *,
    external_id: str | None = None,
    owner_id: str | None = None,
    protein: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    sm = get_sessionmaker()
    async with sm() as db:
        await db.execute(
            text(
                """
                INSERT INTO foods
                  (id, source, external_id, name, protein_g_per_100g,
                   kcal_per_100g, owner_id, payload, created_at, updated_at)
                VALUES
                  (gen_random_uuid(), :source, :external_id, :name, :protein,
                   100, :owner_id, CAST(:payload AS jsonb), NOW(), NOW())
                """
            ),
            {
                "source": source,
                "external_id": external_id,
                "name": name,
                "protein": Decimal(protein) if protein else None,
                "owner_id": owner_id,
                "payload": "{}" if payload is None else __import__("json").dumps(payload),
            },
        )
        await db.commit()


# Search ranking ------------------------------------------------------------


async def test_search_ranks_custom_then_usda_then_off(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    me = (await client.get("/v1/me", headers=headers)).json()
    await _seed_food("off", "Chicken Breast Brand", external_id="111")
    await _seed_food(
        "usda",
        "Chicken Breast Raw",
        external_id="USDA1",
        payload={"category": "foundation_food"},
    )
    await _seed_food("custom", "Chicken Breast Custom", owner_id=me["id"])

    response = await client.get("/v1/foods/search?q=chicken%20breast", headers=headers)
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    names = [i["name"] for i in items]
    assert names.index("Chicken Breast Custom") < names.index("Chicken Breast Raw")
    assert names.index("Chicken Breast Raw") < names.index("Chicken Breast Brand")


async def test_search_filters_by_source_and_min_protein(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    await _seed_food("usda", "Egg White", external_id="USDA2", protein="11")
    await _seed_food("usda", "Egg Whole", external_id="USDA3", protein="6")

    response = await client.get(
        "/v1/foods/search?q=egg&source=usda&min_protein_per_100g=10",
        headers=headers,
    )
    items = response.json()["items"]
    names = [i["name"] for i in items]
    assert "Egg White" in names
    assert "Egg Whole" not in names


async def test_search_short_query_rejected(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    response = await client.get("/v1/foods/search?q=c", headers=headers)
    assert response.status_code == 400


async def test_search_excludes_other_users_custom(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers_a = await _sign_in(client, monkeypatch, sub="user-a")
    user_a = (await client.get("/v1/me", headers=headers_a)).json()
    await _seed_food("custom", "Secret Sauce", owner_id=user_a["id"])

    headers_b = await _sign_in(client, monkeypatch, sub="user-b")
    response = await client.get("/v1/foods/search?q=secret%20sauce", headers=headers_b)
    items = response.json()["items"]
    assert all(i["name"] != "Secret Sauce" for i in items)


# Barcode -------------------------------------------------------------------


async def test_barcode_cache_hit_skips_off(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    await _seed_food("off", "Cached Bar", external_id="012345")

    async def fake_fetch(barcode: str, **kw: Any) -> Any:
        raise AssertionError("OFF should not be called when cache hits")

    monkeypatch.setattr(off, "fetch_product", fake_fetch)

    response = await client.get("/v1/foods/barcode/012345", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Cached Bar"


async def test_barcode_miss_falls_through_to_off_and_caches(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)

    calls: list[str] = []

    async def fake_fetch(barcode: str, **kw: Any) -> off.OffProduct:
        calls.append(barcode)
        return off.OffProduct(
            barcode=barcode,
            name="Live OFF Cookie",
            brand="ACME",
            serving_size_g=Decimal("30.00"),
            serving_label="1 cookie",
            kcal_per_100g=Decimal("450.00"),
            protein_g_per_100g=Decimal("6.00"),
            carbs_g_per_100g=Decimal("70.00"),
            fat_g_per_100g=Decimal("18.00"),
            fiber_g_per_100g=Decimal("2.00"),
        )

    monkeypatch.setattr(off, "fetch_product", fake_fetch)

    first = await client.get("/v1/foods/barcode/999111", headers=headers)
    assert first.status_code == 200
    assert first.json()["name"] == "Live OFF Cookie"
    assert calls == ["999111"]

    # Second call should hit the DB cache, not OFF.
    second = await client.get("/v1/foods/barcode/999111", headers=headers)
    assert second.status_code == 200
    assert calls == ["999111"]
    # Same row.
    assert second.json()["id"] == first.json()["id"]


async def test_barcode_off_not_found_returns_404(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)

    async def fake_fetch(barcode: str, **kw: Any) -> Any:
        raise off.OffNotFoundError(barcode)

    monkeypatch.setattr(off, "fetch_product", fake_fetch)
    response = await client.get("/v1/foods/barcode/000000", headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["message"] == "not_found"


async def test_barcode_off_unreachable_returns_502(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)

    async def fake_fetch(barcode: str, **kw: Any) -> Any:
        raise off.OffClientError("connection refused")

    monkeypatch.setattr(off, "fetch_product", fake_fetch)
    response = await client.get("/v1/foods/barcode/111111", headers=headers)
    assert response.status_code == 502


# Custom CRUD ---------------------------------------------------------------


async def test_custom_food_create_update_delete(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    create = await client.post(
        "/v1/foods",
        headers=headers,
        json={
            "name": "My Protein Shake",
            "kcal_per_100g": "120",
            "protein_g_per_100g": "20",
        },
    )
    assert create.status_code == 201, create.text
    rec = create.json()
    assert rec["source"] == "custom"
    assert rec["owner_id"] is not None

    update = await client.patch(
        f"/v1/foods/{rec['id']}",
        headers=headers,
        json={"kcal_per_100g": "130"},
    )
    assert update.status_code == 200
    assert Decimal(update.json()["kcal_per_100g"]) == Decimal("130.00")

    delete = await client.delete(f"/v1/foods/{rec['id']}", headers=headers)
    assert delete.status_code == 204

    # Search should no longer return it.
    response = await client.get("/v1/foods/search?q=protein%20shake", headers=headers)
    names = [i["name"] for i in response.json()["items"]]
    assert "My Protein Shake" not in names


async def test_custom_food_duplicate_name_409(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    payload = {"name": "Same Name", "kcal_per_100g": "100"}
    first = await client.post("/v1/foods", headers=headers, json=payload)
    assert first.status_code == 201
    second = await client.post("/v1/foods", headers=headers, json=payload)
    assert second.status_code == 409


async def test_other_user_cannot_update_custom_food(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers_a = await _sign_in(client, monkeypatch, sub="ca-a")
    rec = (await client.post("/v1/foods", headers=headers_a, json={"name": "A's Food"})).json()

    headers_b = await _sign_in(client, monkeypatch, sub="ca-b")
    response = await client.patch(
        f"/v1/foods/{rec['id']}", headers=headers_b, json={"name": "Hijacked"}
    )
    assert response.status_code == 404
