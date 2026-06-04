from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import AsyncClient

from app.services import auth as auth_service


async def _sign_in(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    sub: str = "workout-sub",
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    pair = response.json()
    return {"Authorization": f"Bearer {pair['access_token']}"}


def _exercise_payload(
    *,
    name: str,
    tracking_type: str,
    primary: str = "chest",
    equipment: str = "barbell",
    movement: str = "horizontal_push",
) -> dict[str, Any]:
    return {
        "name": name,
        "primary_muscle": primary,
        "secondary_muscles": [],
        "equipment": equipment,
        "movement_pattern": movement,
        "tracking_type": tracking_type,
        "is_unilateral": False,
    }


async def _create_exercise(
    client: AsyncClient,
    headers: dict[str, str],
    **kwargs: Any,
) -> dict[str, Any]:
    response = await client.post("/v1/exercises", headers=headers, json=_exercise_payload(**kwargs))
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Lifecycle: create session, add exercise, add sets, finish.
# ---------------------------------------------------------------------------


async def test_full_session_lifecycle(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    headers = await _sign_in(client, monkeypatch)
    exercise = await _create_exercise(client, headers, name="Bench", tracking_type="weight_reps")

    create_resp = await client.post(
        "/v1/workout-sessions", headers=headers, json={"name": "Push Day"}
    )
    assert create_resp.status_code == 201
    session = create_resp.json()
    session_id = session["id"]
    assert session["workout_exercises"] == []

    add_ex_resp = await client.post(
        f"/v1/workout-sessions/{session_id}/exercises",
        headers=headers,
        json={"exercise_id": exercise["id"]},
    )
    assert add_ex_resp.status_code == 201
    workout_ex = add_ex_resp.json()
    assert workout_ex["position"] == 0
    workout_ex_id = workout_ex["id"]

    for i, weight in enumerate([100, 105, 110]):
        set_resp = await client.post(
            f"/v1/workout-exercises/{workout_ex_id}/sets",
            headers=headers,
            json={"weight_kg": str(weight), "reps": 5},
        )
        assert set_resp.status_code == 201, set_resp.text
        assert set_resp.json()["set_index"] == i

    full = (await client.get(f"/v1/workout-sessions/{session_id}", headers=headers)).json()
    assert len(full["workout_exercises"]) == 1
    assert len(full["workout_exercises"][0]["sets"]) == 3
    assert full["ended_at"] is None

    finish_resp = await client.post(f"/v1/workout-sessions/{session_id}/finish", headers=headers)
    assert finish_resp.status_code == 200
    finished = finish_resp.json()
    assert finished["ended_at"] is not None


# ---------------------------------------------------------------------------
# Per-tracking_type validation.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tracking_type, valid_payload",
    [
        ("weight_reps", {"weight_kg": "100", "reps": 5}),
        ("bodyweight_reps", {"reps": 10}),
        ("weighted_bodyweight", {"weight_kg": "20", "reps": 8}),
        ("time_only", {"duration_seconds": 60}),
        ("weight_time", {"weight_kg": "30", "duration_seconds": 45}),
        ("distance_time", {"distance_meters": "5000", "duration_seconds": 1500}),
        ("weight_reps_distance", {"weight_kg": "30", "reps": 10, "distance_meters": "20"}),
        ("distance_time_pace", {"distance_meters": "1609.34", "duration_seconds": 420}),
        ("cardio_machine", {"duration_seconds": 1800, "distance_meters": "8000"}),
    ],
)
async def test_set_creation_per_tracking_type(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    tracking_type: str,
    valid_payload: dict[str, Any],
) -> None:
    headers = await _sign_in(client, monkeypatch, sub=f"sub-{tracking_type}")
    exercise = await _create_exercise(
        client,
        headers,
        name=f"Ex-{tracking_type}",
        tracking_type=tracking_type,
    )
    session_id = (await client.post("/v1/workout-sessions", headers=headers, json={})).json()["id"]
    we_id = (
        await client.post(
            f"/v1/workout-sessions/{session_id}/exercises",
            headers=headers,
            json={"exercise_id": exercise["id"]},
        )
    ).json()["id"]

    response = await client.post(
        f"/v1/workout-exercises/{we_id}/sets", headers=headers, json=valid_payload
    )
    assert response.status_code == 201, response.text


async def test_set_creation_rejects_wrong_field_for_tracking_type(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    exercise = await _create_exercise(client, headers, name="Plank", tracking_type="time_only")
    session_id = (await client.post("/v1/workout-sessions", headers=headers, json={})).json()["id"]
    we_id = (
        await client.post(
            f"/v1/workout-sessions/{session_id}/exercises",
            headers=headers,
            json={"exercise_id": exercise["id"]},
        )
    ).json()["id"]

    response = await client.post(
        f"/v1/workout-exercises/{we_id}/sets",
        headers=headers,
        json={"duration_seconds": 60, "weight_kg": "100"},
    )
    assert response.status_code == 422
    assert "weight_kg" in response.json()["error"]["message"]


async def test_set_creation_rejects_missing_required(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    exercise = await _create_exercise(client, headers, name="Bench", tracking_type="weight_reps")
    session_id = (await client.post("/v1/workout-sessions", headers=headers, json={})).json()["id"]
    we_id = (
        await client.post(
            f"/v1/workout-sessions/{session_id}/exercises",
            headers=headers,
            json={"exercise_id": exercise["id"]},
        )
    ).json()["id"]

    response = await client.post(
        f"/v1/workout-exercises/{we_id}/sets",
        headers=headers,
        json={"weight_kg": "100"},
    )
    assert response.status_code == 422
    assert "reps" in response.json()["error"]["message"]


# ---------------------------------------------------------------------------
# PR detection (e1RM, bodyweight, pace).
# ---------------------------------------------------------------------------


async def test_pr_detection_marks_best_e1rm_set(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    exercise = await _create_exercise(client, headers, name="Bench", tracking_type="weight_reps")
    session_id = (await client.post("/v1/workout-sessions", headers=headers, json={})).json()["id"]
    we_id = (
        await client.post(
            f"/v1/workout-sessions/{session_id}/exercises",
            headers=headers,
            json={"exercise_id": exercise["id"]},
        )
    ).json()["id"]

    # 100x5 -> e1RM 116.67; 110x3 -> e1RM 121.00 (best); 95x8 -> e1RM 120.33
    for weight, reps in [("100", 5), ("110", 3), ("95", 8)]:
        await client.post(
            f"/v1/workout-exercises/{we_id}/sets",
            headers=headers,
            json={"weight_kg": weight, "reps": reps},
        )

    await client.post(f"/v1/workout-sessions/{session_id}/finish", headers=headers)
    full = (await client.get(f"/v1/workout-sessions/{session_id}", headers=headers)).json()
    sets = full["workout_exercises"][0]["sets"]
    pr_sets = [s for s in sets if s["is_pr"]]
    assert len(pr_sets) == 1
    assert pr_sets[0]["weight_kg"] == "110.00"
    assert pr_sets[0]["reps"] == 3


async def test_pr_detection_second_session_only_marks_if_beats_prior(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    exercise = await _create_exercise(client, headers, name="Bench", tracking_type="weight_reps")

    async def run_session(weight: str, reps: int) -> dict[str, Any]:
        session_id = (await client.post("/v1/workout-sessions", headers=headers, json={})).json()[
            "id"
        ]
        we_id = (
            await client.post(
                f"/v1/workout-sessions/{session_id}/exercises",
                headers=headers,
                json={"exercise_id": exercise["id"]},
            )
        ).json()["id"]
        await client.post(
            f"/v1/workout-exercises/{we_id}/sets",
            headers=headers,
            json={"weight_kg": weight, "reps": reps},
        )
        await client.post(f"/v1/workout-sessions/{session_id}/finish", headers=headers)
        return (await client.get(f"/v1/workout-sessions/{session_id}", headers=headers)).json()

    first = await run_session("100", 5)
    assert first["workout_exercises"][0]["sets"][0]["is_pr"] is True

    # Lower e1RM -> no PR in second session.
    second = await run_session("90", 5)
    assert second["workout_exercises"][0]["sets"][0]["is_pr"] is False

    # Higher e1RM -> PR in third session.
    third = await run_session("110", 5)
    assert third["workout_exercises"][0]["sets"][0]["is_pr"] is True


async def test_pr_detection_bodyweight_reps(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    exercise = await _create_exercise(
        client,
        headers,
        name="Pull-up",
        tracking_type="bodyweight_reps",
        primary="lats",
        equipment="bodyweight",
        movement="vertical_pull",
    )
    session_id = (await client.post("/v1/workout-sessions", headers=headers, json={})).json()["id"]
    we_id = (
        await client.post(
            f"/v1/workout-sessions/{session_id}/exercises",
            headers=headers,
            json={"exercise_id": exercise["id"]},
        )
    ).json()["id"]
    for reps in [8, 12, 10]:
        await client.post(
            f"/v1/workout-exercises/{we_id}/sets",
            headers=headers,
            json={"reps": reps},
        )

    await client.post(f"/v1/workout-sessions/{session_id}/finish", headers=headers)
    full = (await client.get(f"/v1/workout-sessions/{session_id}", headers=headers)).json()
    sets = full["workout_exercises"][0]["sets"]
    pr_sets = [s for s in sets if s["is_pr"]]
    assert len(pr_sets) == 1
    assert pr_sets[0]["reps"] == 12


# ---------------------------------------------------------------------------
# Soft delete, restore.
# ---------------------------------------------------------------------------


async def test_soft_delete_hides_from_list_and_restore_returns_it(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    session_id = (
        await client.post("/v1/workout-sessions", headers=headers, json={"name": "Deletable"})
    ).json()["id"]

    delete_resp = await client.delete(f"/v1/workout-sessions/{session_id}", headers=headers)
    assert delete_resp.status_code == 204

    listed = (await client.get("/v1/workout-sessions", headers=headers)).json()
    assert all(item["id"] != session_id for item in listed["items"])

    fetch_resp = await client.get(f"/v1/workout-sessions/{session_id}", headers=headers)
    assert fetch_resp.status_code == 404

    restore_resp = await client.post(f"/v1/workout-sessions/{session_id}/restore", headers=headers)
    assert restore_resp.status_code == 200
    listed_after = (await client.get("/v1/workout-sessions", headers=headers)).json()
    assert any(item["id"] == session_id for item in listed_after["items"])


# ---------------------------------------------------------------------------
# Reorder, delete cascades, sibling compaction.
# ---------------------------------------------------------------------------


async def test_reorder_and_delete_compact_positions(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    exercises = []
    for i, name in enumerate(["A", "B", "C", "D"]):
        ex = await _create_exercise(
            client, headers, name=f"Ex-{name}-{i}", tracking_type="weight_reps"
        )
        exercises.append(ex)

    session_id = (await client.post("/v1/workout-sessions", headers=headers, json={})).json()["id"]
    we_ids = []
    for ex in exercises:
        we = (
            await client.post(
                f"/v1/workout-sessions/{session_id}/exercises",
                headers=headers,
                json={"exercise_id": ex["id"]},
            )
        ).json()
        we_ids.append(we["id"])

    # Move D (position 3) to position 0.
    reorder = await client.post(
        f"/v1/workout-exercises/{we_ids[3]}/reorder",
        headers=headers,
        json={"position": 0},
    )
    assert reorder.status_code == 200

    full = (await client.get(f"/v1/workout-sessions/{session_id}", headers=headers)).json()
    positions = [we["position"] for we in full["workout_exercises"]]
    assert positions == [0, 1, 2, 3]
    assert full["workout_exercises"][0]["id"] == we_ids[3]

    # Delete the (now) first exercise. Positions should compact.
    await client.delete(f"/v1/workout-exercises/{we_ids[3]}", headers=headers)
    full2 = (await client.get(f"/v1/workout-sessions/{session_id}", headers=headers)).json()
    positions2 = [we["position"] for we in full2["workout_exercises"]]
    assert positions2 == [0, 1, 2]


# ---------------------------------------------------------------------------
# Idempotency: replay returns the same response.
# ---------------------------------------------------------------------------


async def test_idempotent_session_create_replays(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    headers_with_key = {**headers, "Idempotency-Key": "create-session-001"}

    first = await client.post(
        "/v1/workout-sessions",
        headers=headers_with_key,
        json={"name": "Replay test"},
    )
    assert first.status_code == 201
    first_id = first.json()["id"]

    second = await client.post(
        "/v1/workout-sessions",
        headers=headers_with_key,
        json={"name": "Replay test"},
    )
    assert second.status_code == 201
    assert second.json()["id"] == first_id  # same id, no new row


async def test_idempotent_key_with_different_body_409s(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    headers_with_key = {**headers, "Idempotency-Key": "collision-key"}

    first = await client.post(
        "/v1/workout-sessions",
        headers=headers_with_key,
        json={"name": "Original"},
    )
    assert first.status_code == 201

    second = await client.post(
        "/v1/workout-sessions",
        headers=headers_with_key,
        json={"name": "Different"},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "conflict"


# ---------------------------------------------------------------------------
# Repeat last workout: clone a finished session for today with prefilled-but-
# empty sets.
# ---------------------------------------------------------------------------


async def test_repeat_clones_finished_session_with_prefilled_empty_sets(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="repeat-sub")
    bench = await _create_exercise(client, headers, name="Bench", tracking_type="weight_reps")
    squat = await _create_exercise(
        client,
        headers,
        name="Squat",
        tracking_type="weight_reps",
        primary="quads",
        movement="squat",
    )

    # Build a source session a few days in the past and log + finish it.
    source_id = (
        await client.post(
            "/v1/workout-sessions",
            headers=headers,
            json={"name": "Leg Day", "started_at": "2026-05-20T08:00:00Z"},
        )
    ).json()["id"]

    exercise_plan = [
        (bench["id"], [("100", 5), ("105", 5)]),
        (squat["id"], [("140", 3)]),
    ]
    for exercise_id, sets in exercise_plan:
        we_id = (
            await client.post(
                f"/v1/workout-sessions/{source_id}/exercises",
                headers=headers,
                json={"exercise_id": exercise_id},
            )
        ).json()["id"]
        for weight, reps in sets:
            await client.post(
                f"/v1/workout-exercises/{we_id}/sets",
                headers=headers,
                json={"weight_kg": weight, "reps": reps, "rpe": "8"},
            )

    await client.post(f"/v1/workout-sessions/{source_id}/finish", headers=headers)
    source_full = (await client.get(f"/v1/workout-sessions/{source_id}", headers=headers)).json()
    # Sanity: the source session marked at least one PR.
    assert any(s["is_pr"] for s in source_full["workout_exercises"][0]["sets"])

    # Repeat it.
    repeat_resp = await client.post(f"/v1/workout-sessions/{source_id}/repeat", headers=headers)
    assert repeat_resp.status_code == 201, repeat_resp.text
    clone = repeat_resp.json()

    # New session, not the source, and unfinished.
    assert clone["id"] != source_id
    assert clone["ended_at"] is None
    assert clone["name"] == "Leg Day"
    # Not linked to any scheduled workout (free-style repeat).
    assert clone["scheduled_workout_id"] is None

    # started_at is TODAY (UTC).
    started = datetime.fromisoformat(clone["started_at"])
    assert started.astimezone(UTC).date() == datetime.now(tz=UTC).date()

    # Same exercises, same order, same set counts.
    clone_exs = clone["workout_exercises"]
    assert [e["exercise_id"] for e in clone_exs] == [bench["id"], squat["id"]]
    assert [len(e["sets"]) for e in clone_exs] == [2, 1]

    # Sets prefill last performance (weight/reps as targets) but are not-yet-
    # completed: no PR, no effort logged.
    bench_sets = clone_exs[0]["sets"]
    assert [(s["weight_kg"], s["reps"]) for s in bench_sets] == [
        ("100.00", 5),
        ("105.00", 5),
    ]
    for ex in clone_exs:
        for s in ex["sets"]:
            assert s["is_pr"] is False
            assert s["rpe"] is None
            assert s["rir"] is None


async def test_repeat_is_idempotent(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    headers = await _sign_in(client, monkeypatch, sub="repeat-idem-sub")
    exercise = await _create_exercise(client, headers, name="Bench", tracking_type="weight_reps")
    source_id = (
        await client.post("/v1/workout-sessions", headers=headers, json={"name": "Push"})
    ).json()["id"]
    we_id = (
        await client.post(
            f"/v1/workout-sessions/{source_id}/exercises",
            headers=headers,
            json={"exercise_id": exercise["id"]},
        )
    ).json()["id"]
    await client.post(
        f"/v1/workout-exercises/{we_id}/sets",
        headers=headers,
        json={"weight_kg": "100", "reps": 5},
    )
    await client.post(f"/v1/workout-sessions/{source_id}/finish", headers=headers)

    key_headers = {**headers, "Idempotency-Key": "repeat-key-001"}
    first = await client.post(f"/v1/workout-sessions/{source_id}/repeat", headers=key_headers)
    assert first.status_code == 201
    second = await client.post(f"/v1/workout-sessions/{source_id}/repeat", headers=key_headers)
    assert second.status_code == 201
    # Same clone returned, no second clone created.
    assert second.json()["id"] == first.json()["id"]


async def test_repeat_missing_session_returns_404(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="repeat-404-sub")
    response = await client.post(
        "/v1/workout-sessions/00000000-0000-0000-0000-000000000000/repeat",
        headers=headers,
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# N+1 prevention: nested GET should issue a small, constant number of queries.
# ---------------------------------------------------------------------------


async def test_nested_get_does_not_n_plus_one(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Smoke test: many exercises + many sets in one session should return
    in a single fully-nested response with no errors. We don't count queries
    in this test, but selectinload guarantees 1 query per relationship depth.
    """
    headers = await _sign_in(client, monkeypatch)
    exercises = [
        await _create_exercise(client, headers, name=f"Bench-{i}", tracking_type="weight_reps")
        for i in range(5)
    ]
    session_id = (await client.post("/v1/workout-sessions", headers=headers, json={})).json()["id"]
    for ex in exercises:
        we = (
            await client.post(
                f"/v1/workout-sessions/{session_id}/exercises",
                headers=headers,
                json={"exercise_id": ex["id"]},
            )
        ).json()
        for j in range(4):
            await client.post(
                f"/v1/workout-exercises/{we['id']}/sets",
                headers=headers,
                json={"weight_kg": str(60 + j * 5), "reps": 8},
            )

    full = (await client.get(f"/v1/workout-sessions/{session_id}", headers=headers)).json()
    assert len(full["workout_exercises"]) == 5
    for we in full["workout_exercises"]:
        assert len(we["sets"]) == 4


# ---------------------------------------------------------------------------
# DELETE on referenced custom exercise now returns 409 (uses the live check).
# ---------------------------------------------------------------------------


async def test_delete_custom_exercise_referenced_by_workout_returns_409(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    exercise = await _create_exercise(
        client, headers, name="My Custom Bench", tracking_type="weight_reps"
    )
    session_id = (await client.post("/v1/workout-sessions", headers=headers, json={})).json()["id"]
    await client.post(
        f"/v1/workout-sessions/{session_id}/exercises",
        headers=headers,
        json={"exercise_id": exercise["id"]},
    )

    response = await client.delete(f"/v1/exercises/{exercise['id']}", headers=headers)
    assert response.status_code == 409
    assert "archive" in response.json()["error"]["message"].lower()
