from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from app.services import auth as auth_service
from scripts.seed_exercises import seed as seed_exercises
from scripts.seed_programs import seed as seed_programs


async def _sign_in(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    sub: str = "templates-sub",
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_duplicate_creates_independent_fork(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "Base", "goal": "general"})
    ).json()
    await client.post(f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": "Push"})
    dup = await client.post(f"/v1/programs/{prog['id']}/duplicate", headers=headers)
    assert dup.status_code == 201, dup.text
    body = dup.json()["program"]
    assert body["id"] != prog["id"]
    assert body["name"].endswith("(copy)")
    assert body["is_active"] is False
    assert body["template_id"] is None
    assert body["source"] == "copied"
    assert body["microcycle_length"] == 1
    assert [s["name"] for s in body["days"]] == ["Push"]


async def test_duplicate_deep_copies_exercises(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed_exercises()
    headers = await _sign_in(client, monkeypatch, sub="dup-deep")
    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "Base", "goal": "general"})
    ).json()
    slot = (
        await client.post(
            f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": "Push"}
        )
    ).json()
    exercise_id = (await client.get("/v1/exercises?limit=1", headers=headers)).json()["items"][0][
        "id"
    ]
    await client.post(
        f"/v1/program-slots/{slot['id']}/exercises",
        headers=headers,
        json={"exercise_id": exercise_id, "target_sets": 4, "target_reps_low": 6},
    )
    dup = (await client.post(f"/v1/programs/{prog['id']}/duplicate", headers=headers)).json()[
        "program"
    ]
    copied_ex = dup["days"][0]["exercises"]
    assert len(copied_ex) == 1
    assert copied_ex[0]["target_sets"] == 4
    # Distinct rows from the source program.
    src = (await client.get(f"/v1/programs/{prog['id']}", headers=headers)).json()
    assert copied_ex[0]["id"] != src["days"][0]["exercises"][0]["id"]


async def test_save_as_template_then_appears_for_owner(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="save-owner")
    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "Mine", "goal": "general"})
    ).json()
    await client.post(
        f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": "Full body"}
    )
    saved = await client.post(
        f"/v1/programs/{prog['id']}/save-as-template",
        headers=headers,
        json={"name": "My Template", "visibility": "private"},
    )
    assert saved.status_code == 201, saved.text
    body = saved.json()["template"]
    assert body["name"] == "My Template"
    assert body["visibility"] == "private"
    assert body["owner_id"] is not None
    assert body["microcycle_length"] == 1

    listing = (await client.get("/v1/program-templates", headers=headers)).json()
    names = [t["name"] for t in listing["items"]]
    assert "My Template" in names


async def test_private_template_hidden_from_other_user(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    h1 = await _sign_in(client, monkeypatch, sub="user-1")
    prog = (
        await client.post("/v1/programs", headers=h1, json={"name": "P", "goal": "general"})
    ).json()
    await client.post(f"/v1/programs/{prog['id']}/slots", headers=h1, json={"name": "A"})
    await client.post(
        f"/v1/programs/{prog['id']}/save-as-template",
        headers=h1,
        json={"name": "Secret", "visibility": "private"},
    )
    h2 = await _sign_in(client, monkeypatch, sub="user-2")
    listing = (await client.get("/v1/program-templates", headers=h2)).json()
    assert "Secret" not in [t["name"] for t in listing["items"]]


async def test_shared_template_visible_to_other_user(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    h1 = await _sign_in(client, monkeypatch, sub="share-1")
    prog = (
        await client.post("/v1/programs", headers=h1, json={"name": "P", "goal": "general"})
    ).json()
    await client.post(f"/v1/programs/{prog['id']}/slots", headers=h1, json={"name": "A"})
    await client.post(
        f"/v1/programs/{prog['id']}/save-as-template",
        headers=h1,
        json={"name": "Shared Plan", "visibility": "shared"},
    )
    h2 = await _sign_in(client, monkeypatch, sub="share-2")
    listing = (await client.get("/v1/program-templates", headers=h2)).json()
    assert "Shared Plan" in [t["name"] for t in listing["items"]]


async def test_save_as_template_then_copy_yields_slots(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed_exercises()
    headers = await _sign_in(client, monkeypatch, sub="save-copy")
    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "RT", "goal": "general"})
    ).json()
    push = (
        await client.post(
            f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": "Push"}
        )
    ).json()
    await client.post(
        f"/v1/programs/{prog['id']}/slots",
        headers=headers,
        json={"name": "Rest", "is_rest_day": True},
    )
    exercise_id = (await client.get("/v1/exercises?limit=1", headers=headers)).json()["items"][0][
        "id"
    ]
    await client.post(
        f"/v1/program-slots/{push['id']}/exercises",
        headers=headers,
        json={"exercise_id": exercise_id, "target_sets": 3, "target_reps_low": 5},
    )
    saved = await client.post(
        f"/v1/programs/{prog['id']}/save-as-template",
        headers=headers,
        json={"name": "Round Trip", "visibility": "private"},
    )
    slug = saved.json()["template"]["slug"]

    full = (await client.get(f"/v1/program-templates/{slug}", headers=headers)).json()
    assert "slots" in full["data"]
    assert [s["name"] for s in full["data"]["slots"]] == ["Push", "Rest"]
    assert full["data"]["slots"][1]["is_rest_day"] is True

    copy = (await client.post(f"/v1/program-templates/{slug}/copy", headers=headers)).json()
    assert [s["slot_index"] for s in copy["days"]] == [0, 1]
    assert copy["days"][1]["is_rest_day"] is True
    assert len(copy["days"][0]["exercises"]) == 1


async def test_curated_templates_listed_first(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed_exercises()
    await seed_programs()
    headers = await _sign_in(client, monkeypatch, sub="curated-order")
    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})
    ).json()
    await client.post(f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": "A"})
    await client.post(
        f"/v1/programs/{prog['id']}/save-as-template",
        headers=headers,
        json={"name": "ZZZ Mine", "visibility": "private"},
    )
    listing = (await client.get("/v1/program-templates", headers=headers)).json()["items"]
    # 8 curated + 1 owned. Curated (owner_id None) all come before the owned one.
    owner_flags = [t["owner_id"] is None for t in listing]
    first_owned = owner_flags.index(False)
    assert all(owner_flags[:first_owned])
    assert listing[-1]["name"] == "ZZZ Mine"


async def test_template_list_includes_curated(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed_exercises()
    await seed_programs()
    headers = await _sign_in(client, monkeypatch, sub="curated-list")
    listing = (await client.get("/v1/program-templates", headers=headers)).json()["items"]
    slugs = {item["slug"] for item in listing}
    assert "ppl-6day" in slugs
    assert len(listing) == 8
