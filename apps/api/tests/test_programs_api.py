from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from app.services import auth as auth_service
from scripts.seed_exercises import seed as seed_exercises
from scripts.seed_programs import discover_templates
from scripts.seed_programs import seed as seed_programs


async def _sign_in(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    sub: str = "programs-sub",
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    pair = response.json()
    return {"Authorization": f"Bearer {pair['access_token']}"}


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------


async def test_eight_templates_load_with_resolving_slugs() -> None:
    await seed_exercises()
    processed, inserted = await seed_programs()
    assert processed == 8, f"expected 8 templates, got {processed}"
    assert inserted == 8


async def test_program_seed_is_idempotent() -> None:
    await seed_exercises()
    first_processed, first_inserted = await seed_programs()
    second_processed, second_inserted = await seed_programs()
    assert first_processed == 8 and second_processed == 8
    assert first_inserted == 8
    assert second_inserted == 0


def test_dsl_validates_slug_map_at_import() -> None:
    """Every authored template's slug_map covers every referenced slug_key."""
    templates = discover_templates()
    assert len(templates) == 8
    for tpl in templates:
        referenced = {ex.slug_key for d in tpl.days for ex in d.exercises}
        missing = referenced - tpl.slug_map.keys()
        assert not missing, f"{tpl.slug}: {missing} not in slug_map"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


async def test_list_templates_endpoint(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed_exercises()
    await seed_programs()
    headers = await _sign_in(client, monkeypatch)

    response = await client.get("/v1/program-templates", headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 8
    slugs = {item["slug"] for item in items}
    assert {
        "ppl-6day",
        "upper-lower-4day",
        "arnold-split-6day",
        "bro-split-5day",
        "531-bbb-4day",
        "starting-strength-3day",
        "nsuns-531-lp-5day",
        "push-pull-4day",
    } <= slugs


async def test_get_template_full_returns_nested_data(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed_exercises()
    await seed_programs()
    headers = await _sign_in(client, monkeypatch)

    response = await client.get("/v1/program-templates/ppl-6day", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "ppl-6day"
    # 6 training slots + 1 explicit rest slot = a 7-slot weekly microcycle.
    assert body["microcycle_length"] == 7
    assert "data" in body and isinstance(body["data"], dict)
    assert len(body["data"]["slots"]) == 7
    training = [s for s in body["data"]["slots"] if not s["is_rest_day"]]
    rest = [s for s in body["data"]["slots"] if s["is_rest_day"]]
    assert len(training) == 6
    assert len(rest) == 1


async def test_get_unknown_template_returns_404(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    response = await client.get("/v1/program-templates/does-not-exist", headers=headers)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Copy
# ---------------------------------------------------------------------------


async def test_copy_template_creates_owned_program(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed_exercises()
    await seed_programs()
    headers = await _sign_in(client, monkeypatch)

    response = await client.post(
        "/v1/program-templates/starting-strength-3day/copy", headers=headers
    )
    assert response.status_code == 201, response.text
    program = response.json()
    assert program["source"] == "template"
    assert program["template_id"] is not None
    assert program["name"] == "Starting Strength (3-day)"
    # 3 training slots + 4 explicit rest slots = a 7-slot weekly microcycle.
    assert program["microcycle_length"] == 7
    assert len(program["days"]) == 7
    training_days = [d for d in program["days"] if not d["is_rest_day"]]
    rest_days = [d for d in program["days"] if d["is_rest_day"]]
    assert len(training_days) == 3
    assert len(rest_days) == 4
    # Each rest slot carries no exercises; each training slot has loaded sets.
    for day in rest_days:
        assert day["exercises"] == []
    for day in training_days:
        assert len(day["exercises"]) > 0
        for ex in day["exercises"]:
            assert ex["target_sets"] >= 1


async def test_second_copy_disambiguates_name(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed_exercises()
    await seed_programs()
    headers = await _sign_in(client, monkeypatch)

    first = await client.post("/v1/program-templates/ppl-6day/copy", headers=headers)
    assert first.status_code == 201
    second = await client.post("/v1/program-templates/ppl-6day/copy", headers=headers)
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert second.json()["name"].endswith("(2)")


async def test_copy_structure_matches_template(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The copied program's nested structure mirrors the template data."""
    await seed_exercises()
    await seed_programs()
    headers = await _sign_in(client, monkeypatch)

    template = (await client.get("/v1/program-templates/upper-lower-4day", headers=headers)).json()
    copy = (
        await client.post("/v1/program-templates/upper-lower-4day/copy", headers=headers)
    ).json()

    template_days = template["data"]["slots"]
    program_days = copy["days"]
    assert len(template_days) == len(program_days)
    for t_day, p_day in zip(template_days, program_days, strict=True):
        assert t_day["name"] == p_day["name"]
        assert len(t_day["exercises"]) == len(p_day["exercises"])
        for t_ex, p_ex in zip(t_day["exercises"], p_day["exercises"], strict=True):
            assert t_ex["sets"] == p_ex["target_sets"]
            if "reps_low" in t_ex:
                assert t_ex["reps_low"] == p_ex["target_reps_low"]
            if "reps_high" in t_ex:
                assert t_ex["reps_high"] == p_ex["target_reps_high"]
            if "rest_seconds" in t_ex:
                assert t_ex["rest_seconds"] == p_ex["rest_seconds"]


async def test_copy_derives_intensity_mode_rpe(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A template whose exercises carry rpe values copies to intensity_mode 'rpe'."""
    await seed_exercises()
    await seed_programs()
    headers = await _sign_in(client, monkeypatch)

    copy = (await client.post("/v1/program-templates/ppl-6day/copy", headers=headers)).json()
    assert copy["intensity_mode"] == "rpe"


async def test_copy_derives_per_exercise_rep_mode(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Range vs target is derived from each template exercise's reps span.

    Starting Strength mixes fixed-rep main lifts (reps=5, which the DSL expands
    to low==high==5 -> 'target') with a ranged accessory (pull-ups reps=(5, 10)
    -> 'range').
    """
    await seed_exercises()
    await seed_programs()
    headers = await _sign_in(client, monkeypatch)

    copy = (
        await client.post("/v1/program-templates/starting-strength-3day/copy", headers=headers)
    ).json()

    modes_by_reps: dict[tuple[int | None, int | None], set[str]] = {}
    for day in copy["days"]:
        for ex in day["exercises"]:
            key = (ex["target_reps_low"], ex["target_reps_high"])
            modes_by_reps.setdefault(key, set()).add(ex["rep_mode"])

    # Fixed single goal (low == high) -> target.
    assert modes_by_reps[(5, 5)] == {"target"}
    assert modes_by_reps[(3, 3)] == {"target"}
    # Spanned accessory -> range.
    assert modes_by_reps[(5, 10)] == {"range"}


async def test_unauthenticated_template_list_is_401(client: AsyncClient) -> None:
    response = await client.get("/v1/program-templates")
    assert response.status_code == 401
