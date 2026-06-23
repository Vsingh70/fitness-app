from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from app.services import auth as auth_service


async def _sign_in(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    sub: str = "slots-sub",
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_add_reorder_and_rest_toggle_slots(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})
    ).json()
    a = (
        await client.post(
            f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": "Push"}
        )
    ).json()
    b = (
        await client.post(
            f"/v1/programs/{prog['id']}/slots",
            headers=headers,
            json={"name": "Rest", "is_rest_day": True},
        )
    ).json()
    full = (await client.get(f"/v1/programs/{prog['id']}", headers=headers)).json()
    assert full["microcycle_length"] == 2
    assert [s["slot_index"] for s in full["days"]] == [0, 1]
    assert full["days"][1]["is_rest_day"] is True

    # reorder
    reorder = await client.post(
        f"/v1/programs/{prog['id']}/slots/reorder",
        headers=headers,
        json={"slot_ids": [b["id"], a["id"]]},
    )
    assert reorder.status_code == 200, reorder.text
    full2 = (await client.get(f"/v1/programs/{prog['id']}", headers=headers)).json()
    assert full2["days"][0]["id"] == b["id"]
    assert [s["slot_index"] for s in full2["days"]] == [0, 1]


async def test_reorder_rejects_wrong_id_set(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="slots-reorder-bad")
    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})
    ).json()
    a = (
        await client.post(f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": "A"})
    ).json()
    await client.post(f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": "B"})
    # Missing one slot id -> 422.
    bad = await client.post(
        f"/v1/programs/{prog['id']}/slots/reorder",
        headers=headers,
        json={"slot_ids": [a["id"]]},
    )
    assert bad.status_code == 422


async def test_delete_slot_reindexes_and_recomputes_length(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="slots-delete")
    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})
    ).json()
    ids = []
    for name in ["A", "B", "C"]:
        slot = (
            await client.post(
                f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": name}
            )
        ).json()
        ids.append(slot["id"])

    delete = await client.delete(f"/v1/program-slots/{ids[0]}", headers=headers)
    assert delete.status_code == 204

    full = (await client.get(f"/v1/programs/{prog['id']}", headers=headers)).json()
    assert full["microcycle_length"] == 2
    assert [s["slot_index"] for s in full["days"]] == [0, 1]
    assert [s["name"] for s in full["days"]] == ["B", "C"]


async def test_toggle_rest_keeps_exercises(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.seed_exercises import seed as seed_exercises

    await seed_exercises()
    headers = await _sign_in(client, monkeypatch, sub="slots-toggle")
    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})
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
        json={"exercise_id": exercise_id, "target_sets": 3, "target_reps_low": 5},
    )

    # Flip to rest: exercise rows persist.
    rest = await client.patch(
        f"/v1/program-slots/{slot['id']}", headers=headers, json={"is_rest_day": True}
    )
    assert rest.status_code == 200, rest.text
    body = rest.json()
    assert body["days"][0]["is_rest_day"] is True
    assert len(body["days"][0]["exercises"]) == 1

    # Flip back to training: exercises still there.
    back = await client.patch(
        f"/v1/program-slots/{slot['id']}", headers=headers, json={"is_rest_day": False}
    )
    assert back.status_code == 200
    assert back.json()["days"][0]["is_rest_day"] is False
    assert len(back.json()["days"][0]["exercises"]) == 1


async def test_activate_requires_one_training_slot(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="slots-activate")
    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})
    ).json()
    # rest-only -> cannot activate
    await client.post(
        f"/v1/programs/{prog['id']}/slots",
        headers=headers,
        json={"name": "Rest", "is_rest_day": True},
    )
    bad = await client.post(f"/v1/programs/{prog['id']}/activate", headers=headers)
    assert bad.status_code == 422
    # add a training slot -> activates
    await client.post(f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": "Push"})
    ok = await client.post(f"/v1/programs/{prog['id']}/activate", headers=headers)
    assert ok.status_code == 200
    assert ok.json()["is_active"] is True


async def test_activate_empty_program_is_422(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="slots-empty-activate")
    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})
    ).json()
    bad = await client.post(f"/v1/programs/{prog['id']}/activate", headers=headers)
    assert bad.status_code == 422


async def test_activating_one_deactivates_the_other(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="slots-single-active")
    ids = []
    for _ in range(2):
        prog = (
            await client.post(
                "/v1/programs", headers=headers, json={"name": "P", "goal": "general"}
            )
        ).json()
        await client.post(
            f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": "Push"}
        )
        await client.post(f"/v1/programs/{prog['id']}/activate", headers=headers)
        ids.append(prog["id"])

    listed = (await client.get("/v1/programs", headers=headers)).json()
    actives = [item for item in listed["items"] if item["is_active"]]
    assert len(actives) == 1
    assert actives[0]["id"] == ids[1]


async def test_deactivate_clears_is_active(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="slots-deactivate")
    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})
    ).json()
    await client.post(f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": "Push"})
    await client.post(f"/v1/programs/{prog['id']}/activate", headers=headers)

    deactivate = await client.post(f"/v1/programs/{prog['id']}/deactivate", headers=headers)
    assert deactivate.status_code == 200
    assert deactivate.json()["is_active"] is False
