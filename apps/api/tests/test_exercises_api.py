from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient

from app.services import auth as auth_service
from scripts.seed_exercises import seed


async def _sign_in(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    sub: str = "apple-exercises-sub",
    email: str | None = None,
) -> dict[str, str]:
    effective_email = email or f"{sub}@example.com"

    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=effective_email)

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    pair = response.json()
    return {"Authorization": f"Bearer {pair['access_token']}"}


def _exercise_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "name": "Custom Pause Bench Press",
        "primary_muscle": "chest",
        "secondary_muscles": ["triceps", "front_delts"],
        "equipment": "barbell",
        "movement_pattern": "horizontal_push",
        "tracking_type": "weight_reps",
        "is_unilateral": False,
        "notes": "3-second pause at the bottom.",
    }
    base.update(overrides)
    return base


async def test_list_exercises_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/v1/exercises")
    assert response.status_code == 401


async def test_search_returns_bench_variants(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed()
    headers = await _sign_in(client, monkeypatch)

    response = await client.get("/v1/exercises?q=bench&limit=200", headers=headers)
    assert response.status_code == 200
    names = [item["name"].lower() for item in response.json()["items"]]
    assert any("bench press" in n for n in names)
    assert any("incline" in n and "bench" in n for n in names)
    assert any("dumbbell" in n and "bench" in n for n in names)


async def test_muscle_filter_includes_primary_and_secondary(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed()
    headers = await _sign_in(client, monkeypatch)

    response = await client.get(
        "/v1/exercises?muscle=triceps&limit=200", headers=headers
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert items, "expected triceps results"
    for item in items:
        targets_triceps = (
            item["primary_muscle"] == "triceps" or "triceps" in item["secondary_muscles"]
        )
        assert targets_triceps, f"{item['name']} returned but doesn't target triceps"


async def test_create_custom_exercise_returns_201(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    response = await client.post(
        "/v1/exercises", headers=headers, json=_exercise_payload()
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["owner_id"] is not None
    assert body["slug"].startswith("custom-pause-bench-press")


async def test_custom_exercise_visible_to_owner_not_others(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner_headers = await _sign_in(client, monkeypatch, sub="owner-sub")
    created = await client.post(
        "/v1/exercises", headers=owner_headers, json=_exercise_payload(name="Owner Special")
    )
    assert created.status_code == 201
    exercise_id = created.json()["id"]

    # Owner can fetch.
    own_fetch = await client.get(f"/v1/exercises/{exercise_id}", headers=owner_headers)
    assert own_fetch.status_code == 200

    # Different user cannot.
    other_headers = await _sign_in(client, monkeypatch, sub="other-sub")
    other_fetch = await client.get(f"/v1/exercises/{exercise_id}", headers=other_headers)
    assert other_fetch.status_code == 404


async def test_user_cannot_edit_or_delete_curated(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed()
    headers = await _sign_in(client, monkeypatch)

    listed = (
        await client.get("/v1/exercises?limit=1", headers=headers)
    ).json()["items"]
    assert listed, "seed should provide at least one curated exercise"
    curated_id = listed[0]["id"]

    patch = await client.patch(
        f"/v1/exercises/{curated_id}",
        headers=headers,
        json={"notes": "tampered"},
    )
    assert patch.status_code == 403
    assert patch.json()["error"]["code"] == "forbidden"

    delete = await client.delete(f"/v1/exercises/{curated_id}", headers=headers)
    assert delete.status_code == 403


async def test_user_can_archive_their_custom_exercise(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    created = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    exercise_id = created["id"]

    archived = await client.post(
        f"/v1/exercises/{exercise_id}/archive", headers=headers
    )
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None

    # Default list excludes archived.
    listed = await client.get("/v1/exercises?mine_only=true", headers=headers)
    ids_listed = {item["id"] for item in listed.json()["items"]}
    assert exercise_id not in ids_listed

    # include_archived=true returns it.
    with_archived = await client.get(
        "/v1/exercises?mine_only=true&include_archived=true", headers=headers
    )
    ids_with_archived = {item["id"] for item in with_archived.json()["items"]}
    assert exercise_id in ids_with_archived


async def test_user_can_delete_their_custom_exercise(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    created = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    exercise_id = created["id"]

    deleted = await client.delete(f"/v1/exercises/{exercise_id}", headers=headers)
    assert deleted.status_code == 204

    after = await client.get(f"/v1/exercises/{exercise_id}", headers=headers)
    assert after.status_code == 404


async def test_pagination_cursor_round_trip(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed()
    headers = await _sign_in(client, monkeypatch)

    page1 = (await client.get("/v1/exercises?limit=10", headers=headers)).json()
    assert len(page1["items"]) == 10
    assert page1["next_cursor"] is not None

    page2 = (
        await client.get(
            f"/v1/exercises?limit=10&cursor={page1['next_cursor']}", headers=headers
        )
    ).json()
    ids_page1 = {item["id"] for item in page1["items"]}
    ids_page2 = {item["id"] for item in page2["items"]}
    assert ids_page1.isdisjoint(ids_page2), "pages should not overlap"


async def test_invalid_uuid_is_404(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    response = await client.get(
        f"/v1/exercises/{UUID(int=0)}", headers=headers
    )
    assert response.status_code == 404
