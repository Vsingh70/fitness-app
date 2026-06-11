"""End-to-end: finishing a scheduled session calls the rationale pipeline and
persists the result on the recommendation row.

The autouse `stub_rationale_pipeline` fixture in conftest already runs the job
inline. Individual tests here override `app.clients.ollama.generate` to control
what the LLM "returns".
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from app.clients import ollama as ollama_module
from app.services import auth as auth_service


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "rationale-sub"
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _exercise_payload() -> dict[str, Any]:
    return {
        "name": "Bench (rationale test)",
        "primary_muscle": "chest",
        "secondary_muscles": ["triceps"],
        "equipment": "barbell",
        "movement_pattern": "horizontal_push",
        "tracking_type": "weight_reps",
        "is_unilateral": False,
    }


async def _create_linear_program(
    client: AsyncClient, headers: dict[str, str], exercise_id: str
) -> str:
    program = (
        await client.post(
            "/v1/programs",
            headers=headers,
            json={
                "name": "Rationale Prog",
                "goal": "strength",
                "weeks": 2,
                "days_per_week": 1,
            },
        )
    ).json()
    day = (
        await client.post(
            f"/v1/programs/{program['id']}/days",
            headers=headers,
            json={"name": "Day 1"},
        )
    ).json()
    await client.post(
        f"/v1/program-days/{day['id']}/exercises",
        headers=headers,
        json={
            "exercise_id": exercise_id,
            "target_sets": 3,
            "target_reps_low": 5,
            "progression_strategy": "linear",
        },
    )
    return program["id"]


async def _activate(client: AsyncClient, headers: dict[str, str], program_id: str) -> None:
    response = await client.post(
        f"/v1/programs/{program_id}/activate",
        headers=headers,
        json={"start_date": "2026-06-01", "weekday_offset": 0, "skip_existing": True},
    )
    assert response.status_code == 200, response.text


async def _finish_clean_session(
    client: AsyncClient, headers: dict[str, str], scheduled_id: str, *, weight: str
) -> None:
    workout = (
        await client.post(f"/v1/scheduled-workouts/{scheduled_id}/start", headers=headers)
    ).json()
    we_id = workout["workout_exercises"][0]["id"]
    for _ in range(3):
        await client.post(
            f"/v1/workout-exercises/{we_id}/sets",
            headers=headers,
            json={"weight_kg": weight, "reps": 5, "set_type": "working"},
        )
    finish = await client.post(f"/v1/workout-sessions/{workout['id']}/finish", headers=headers)
    assert finish.status_code == 200, finish.text


async def test_rationale_persisted_when_ollama_returns_clean_output(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_generate(**kwargs: Any) -> str:
        return "You hit all three sets at 60 kg, so weight goes up to 62.5 kg next session."

    monkeypatch.setattr(ollama_module, "generate", fake_generate)

    headers = await _sign_in(client, monkeypatch)
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    program_id = await _create_linear_program(client, headers, exercise["id"])
    await _activate(client, headers, program_id)
    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    await _finish_clean_session(client, headers, scheduled[0]["id"], weight="60")

    recs = (await client.get("/v1/recommendations", headers=headers)).json()["items"]
    assert len(recs) == 1
    assert (
        recs[0]["rationale"]
        == "You hit all three sets at 60 kg, so weight goes up to 62.5 kg next session."
    )


async def test_rationale_falls_back_when_ollama_is_unavailable(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Default conftest fixture already makes ollama.generate raise; that's
    # what an outage looks like.
    headers = await _sign_in(client, monkeypatch)
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    program_id = await _create_linear_program(client, headers, exercise["id"])
    await _activate(client, headers, program_id)
    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    await _finish_clean_session(client, headers, scheduled[0]["id"], weight="60")

    recs = (await client.get("/v1/recommendations", headers=headers)).json()["items"]
    assert len(recs) == 1
    # Linear strategy with prior=60, next=62.5 -> increment_kg=2.50.
    assert recs[0]["rationale"] == "You hit all sets, so weight is going up by 2.50 kg next time."


async def test_rationale_falls_back_when_ollama_returns_banned_chars(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_generate(**kwargs: Any) -> str:
        # Em dash is forbidden, validator rejects, fallback kicks in.
        return "Great session — weight is moving up."

    monkeypatch.setattr(ollama_module, "generate", fake_generate)

    headers = await _sign_in(client, monkeypatch)
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload())
    ).json()
    program_id = await _create_linear_program(client, headers, exercise["id"])
    await _activate(client, headers, program_id)
    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    await _finish_clean_session(client, headers, scheduled[0]["id"], weight="60")

    recs = (await client.get("/v1/recommendations", headers=headers)).json()["items"]
    assert recs[0]["rationale"] == "You hit all sets, so weight is going up by 2.50 kg next time."
