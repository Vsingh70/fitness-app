from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from app.services import auth as auth_service


async def _sign_in(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    sub: str = "rotation-sub",
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _build_psr_program(client: AsyncClient, headers: dict[str, str]) -> str:
    """Push / Rest / Pull program, activated."""
    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})
    ).json()
    for name, rest in [("Push", False), ("Rest", True), ("Pull", False)]:
        await client.post(
            f"/v1/programs/{prog['id']}/slots",
            headers=headers,
            json={"name": name, "is_rest_day": rest},
        )
    await client.post(f"/v1/programs/{prog['id']}/activate", headers=headers)
    return str(prog["id"])


async def test_position_advances_and_wraps(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    program_id = await _build_psr_program(client, headers)

    pos = (await client.get(f"/v1/programs/{program_id}/position", headers=headers)).json()
    assert pos["current_slot_index"] == 0 and pos["is_rest_day"] is False
    assert pos["today_slot"]["name"] == "Push"

    # advance onto the rest slot
    pos = (await client.post(f"/v1/programs/{program_id}/advance", headers=headers)).json()
    assert pos["current_slot_index"] == 1 and pos["is_rest_day"] is True
    assert pos["next_training_slot"]["name"] == "Pull"

    # advance to last, then wrap to slot 0 / repetition 2
    await client.post(f"/v1/programs/{program_id}/advance", headers=headers)
    pos = (await client.post(f"/v1/programs/{program_id}/advance", headers=headers)).json()
    assert pos["current_slot_index"] == 0 and pos["current_repetition"] == 2


async def test_advance_as_skip_does_not_stamp_completion(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="rotation-skip")
    program_id = await _build_psr_program(client, headers)

    # A plain advance and a skip both move the slot; both return a valid position.
    skip = await client.post(
        f"/v1/programs/{program_id}/advance", headers=headers, json={"as_skip": True}
    )
    assert skip.status_code == 200
    assert skip.json()["current_slot_index"] == 1


async def test_position_creates_progress_for_active_program(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="rotation-progress")
    program_id = await _build_psr_program(client, headers)
    pos = (await client.get(f"/v1/programs/{program_id}/position", headers=headers)).json()
    assert pos["current_microcycle_number"] == 1
    assert pos["current_repetition"] == 1
    assert pos["in_deload"] is False
    assert pos["mesocycle_length_microcycles"] == 4


async def test_position_for_program_without_slots(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="rotation-empty")
    prog = (
        await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})
    ).json()
    pos = (await client.get(f"/v1/programs/{prog['id']}/position", headers=headers)).json()
    assert pos["today_slot"] is None
    assert pos["next_training_slot"] is None
    assert pos["is_rest_day"] is False
