"""Cursor pagination on /meals, /meal-plans, /programs, /recommendations and
the `ids` filter on /exercises (perf pass)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.db import get_sessionmaker
from app.services import auth as auth_service
from app.services.pagination import encode_cursor


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "pagination-sub"
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _exercise_payload(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "primary_muscle": "chest",
        "secondary_muscles": [],
        "equipment": "barbell",
        "movement_pattern": "horizontal_push",
        "tracking_type": "weight_reps",
        "is_unilateral": False,
    }


# ---------------------------------------------------------------------------
# /meals
# ---------------------------------------------------------------------------


async def test_meals_pagination_cursor_walk(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="meals-page-sub")
    for hour in range(5):
        created = await client.post(
            "/v1/meals",
            headers=headers,
            json={"eaten_at": f"2026-06-01T{8 + hour:02d}:00:00Z", "meal_type": "snack"},
        )
        assert created.status_code == 201

    page1 = (await client.get("/v1/meals?limit=2", headers=headers)).json()
    assert len(page1["items"]) == 2
    assert page1["next_cursor"] is not None

    page2 = (
        await client.get(f"/v1/meals?limit=2&cursor={page1['next_cursor']}", headers=headers)
    ).json()
    assert len(page2["items"]) == 2
    assert page2["next_cursor"] is not None

    page3 = (
        await client.get(f"/v1/meals?limit=2&cursor={page2['next_cursor']}", headers=headers)
    ).json()
    assert len(page3["items"]) == 1
    assert page3["next_cursor"] is None

    eaten = [m["eaten_at"] for m in page1["items"] + page2["items"] + page3["items"]]
    assert eaten == sorted(eaten)  # chronological, no overlap
    ids = [m["id"] for m in page1["items"] + page2["items"] + page3["items"]]
    assert len(set(ids)) == 5


async def test_meals_invalid_cursor_is_400(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="meals-cursor-sub")
    response = await client.get("/v1/meals?cursor=not-a-cursor", headers=headers)
    assert response.status_code == 400


async def test_meals_cursor_with_non_string_values_is_400(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="meals-badcursor-sub")
    # Well-formed base64/JSON but wrong value types: must be 400, not 500.
    bad = encode_cursor({"c": 1, "i": 2})
    response = await client.get(f"/v1/meals?cursor={bad}", headers=headers)
    assert response.status_code == 400


async def test_recommendations_cursor_with_non_string_values_is_400(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="recs-badcursor-sub")
    bad = encode_cursor({"c": 1, "i": 2})
    response = await client.get(f"/v1/recommendations?cursor={bad}", headers=headers)
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# /meal-plans
# ---------------------------------------------------------------------------


async def test_meal_plans_pagination_active_first(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="plans-page-sub")
    plan_ids: list[str] = []
    for label in ("A", "B", "C"):
        created = await client.post(
            "/v1/meal-plans",
            headers=headers,
            json={"name": f"Plan {label}", "content_mode": "targets_only", "target_kcal": "2000"},
        )
        assert created.status_code == 201, created.text
        plan_ids.append(created.json()["id"])
    # Activate the OLDEST plan so the (is_active desc, created_at desc) ordering
    # is exercised across the cursor boundary.
    activated = await client.post(f"/v1/meal-plans/{plan_ids[0]}/activate", headers=headers)
    assert activated.status_code == 200

    page1 = (await client.get("/v1/meal-plans?limit=2", headers=headers)).json()
    assert len(page1["items"]) == 2
    assert page1["items"][0]["id"] == plan_ids[0]  # active plan first
    assert page1["next_cursor"] is not None

    page2 = (
        await client.get(f"/v1/meal-plans?limit=2&cursor={page1['next_cursor']}", headers=headers)
    ).json()
    assert len(page2["items"]) == 1
    assert page2["next_cursor"] is None

    seen = [p["id"] for p in page1["items"] + page2["items"]]
    assert sorted(seen) == sorted(plan_ids)


# ---------------------------------------------------------------------------
# /programs
# ---------------------------------------------------------------------------


async def test_programs_pagination_cursor_walk(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="programs-page-sub")
    program_ids: list[str] = []
    for label in ("A", "B", "C"):
        created = await client.post(
            "/v1/programs",
            headers=headers,
            json={
                "name": f"Program {label}",
                "goal": "hypertrophy",
            },
        )
        assert created.status_code == 201, created.text
        program_ids.append(created.json()["id"])

    page1 = (await client.get("/v1/programs?limit=2", headers=headers)).json()
    assert len(page1["items"]) == 2
    assert page1["next_cursor"] is not None

    page2 = (
        await client.get(f"/v1/programs?limit=2&cursor={page1['next_cursor']}", headers=headers)
    ).json()
    assert len(page2["items"]) == 1
    assert page2["next_cursor"] is None

    seen = [p["id"] for p in page1["items"] + page2["items"]]
    assert sorted(seen) == sorted(program_ids)


# ---------------------------------------------------------------------------
# /recommendations
# ---------------------------------------------------------------------------


async def _seed_recommendations(user_id: str, exercise_id: str, count: int) -> None:
    sm = get_sessionmaker()
    async with sm() as db:
        for i in range(count):
            await db.execute(
                text(
                    """
                    INSERT INTO recommendations
                        (id, user_id, exercise_id, kind, payload, created_at, updated_at)
                    VALUES
                        (gen_random_uuid(), :user_id, :exercise_id, 'hold', '{}'::jsonb,
                         NOW() - make_interval(mins => :age), NOW())
                    """
                ),
                {"user_id": user_id, "exercise_id": exercise_id, "age": i},
            )
        await db.commit()


async def test_recommendations_pagination_cursor_walk(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="recs-page-sub")
    me = (await client.get("/v1/me", headers=headers)).json()
    exercise = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload("Recs Bench"))
    ).json()
    await _seed_recommendations(me["id"], exercise["id"], 3)

    page1 = (await client.get("/v1/recommendations?limit=2", headers=headers)).json()
    assert len(page1["items"]) == 2
    assert page1["next_cursor"] is not None

    page2 = (
        await client.get(
            f"/v1/recommendations?limit=2&cursor={page1['next_cursor']}", headers=headers
        )
    ).json()
    assert len(page2["items"]) == 1
    assert page2["next_cursor"] is None

    created = [r["created_at"] for r in page1["items"] + page2["items"]]
    assert created == sorted(created, reverse=True)  # newest first, no overlap
    assert len({r["id"] for r in page1["items"] + page2["items"]}) == 3


# ---------------------------------------------------------------------------
# /exercises?ids=...
# ---------------------------------------------------------------------------


async def test_exercises_ids_filter_returns_exact_set(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="ids-filter-sub")
    created_ids = []
    for n in range(3):
        created = await client.post(
            "/v1/exercises", headers=headers, json=_exercise_payload(f"Ids Filter Lift {n}")
        )
        assert created.status_code == 201
        created_ids.append(created.json()["id"])

    wanted = created_ids[:2]
    response = await client.get(
        "/v1/exercises", headers=headers, params=[("ids", i) for i in wanted]
    )
    assert response.status_code == 200
    body = response.json()
    assert sorted(item["id"] for item in body["items"]) == sorted(wanted)
    assert body["next_cursor"] is None


async def test_exercises_ids_filter_respects_visibility(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    other_headers = await _sign_in(client, monkeypatch, sub="ids-other-sub")
    other_exercise = (
        await client.post(
            "/v1/exercises", headers=other_headers, json=_exercise_payload("Other Private Lift")
        )
    ).json()

    headers = await _sign_in(client, monkeypatch, sub="ids-viewer-sub")
    mine = (
        await client.post("/v1/exercises", headers=headers, json=_exercise_payload("My Lift"))
    ).json()

    response = await client.get(
        "/v1/exercises",
        headers=headers,
        params=[("ids", mine["id"]), ("ids", other_exercise["id"])],
    )
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [mine["id"]]  # the other user's custom exercise is invisible


async def test_exercises_ids_filter_caps_at_100(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="ids-cap-sub")
    response = await client.get(
        "/v1/exercises",
        headers=headers,
        params=[("ids", str(uuid4())) for _ in range(101)],
    )
    assert response.status_code == 400
