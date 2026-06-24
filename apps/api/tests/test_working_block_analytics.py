"""Task C (06 §6): working-block-only analytics + segment-summed reps.

Working-volume rollups, per-muscle analytics, and PR detection count ONLY
``working`` blocks. Rest-pause/cluster total reps come from the sum of
``mini_set`` segment reps. Skipped sessions are ignored.

- A warm-up/cooldown block of varied movements is logged but never counted as
  training volume, and a warm-up single is never a PR.
- A 10+3+2 rest-pause set counts as 15 reps for tonnage and for the e1RM PR.
- A skipped session contributes no volume.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from app.db import get_sessionmaker
from app.models.scheduled_workout import ScheduledWorkout
from app.services import auth as auth_service
from tests._scheduling_helpers import seed_scheduled_for_program


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _make_exercise(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    name: str,
    primary: str = "chest",
    secondary: list[str] | None = None,
    tracking_type: str = "weight_reps",
    movement: str = "horizontal_push",
    equipment: str = "barbell",
) -> dict[str, Any]:
    payload = {
        "name": name,
        "primary_muscle": primary,
        "secondary_muscles": secondary or [],
        "equipment": equipment,
        "movement_pattern": movement,
        "tracking_type": tracking_type,
        "is_unilateral": False,
    }
    return (await client.post("/v1/exercises", headers=headers, json=payload)).json()


async def _backdate(session_id: str, on_date: date) -> None:
    sm = get_sessionmaker()
    async with sm() as db:
        await db.execute(
            text("UPDATE workout_sessions SET started_at = :ts WHERE id = :id"),
            {
                "ts": datetime.combine(on_date, datetime.min.time().replace(hour=12), tzinfo=UTC),
                "id": session_id,
            },
        )
        await db.commit()


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


# ---------------------------------------------------------------------------
# Block kind: warm-up / cooldown blocks are excluded from volume and PRs.
# ---------------------------------------------------------------------------


async def test_warmup_block_excluded_from_volume_and_prs(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="block-vol-sub")
    bench = await _make_exercise(client, headers, name="Bench", primary="chest")
    mobility = await _make_exercise(
        client,
        headers,
        name="Band Pull-Apart",
        primary="rear_delts",
        tracking_type="bodyweight_reps",
        movement="mobility",
        equipment="banded",
    )

    target = _monday(date(2026, 6, 1))
    iy, iw, _ = target.isocalendar()
    session_id = (await client.post("/v1/workout-sessions", headers=headers, json={})).json()["id"]
    await _backdate(session_id, target)

    # A warm-up block of a different movement: logged, but never counted.
    warmup_we = (
        await client.post(
            f"/v1/workout-sessions/{session_id}/exercises",
            headers=headers,
            json={
                "exercise_id": mobility["id"],
                "block_kind": "warmup",
                "block_label": "Mobility",
            },
        )
    ).json()
    await client.post(
        f"/v1/workout-exercises/{warmup_we['id']}/sets",
        headers=headers,
        json={"reps": 20, "set_type": "working"},
    )

    # The working block: this is the only thing that counts.
    working_we = (
        await client.post(
            f"/v1/workout-sessions/{session_id}/exercises",
            headers=headers,
            json={"exercise_id": bench["id"]},
        )
    ).json()
    await client.post(
        f"/v1/workout-exercises/{working_we['id']}/sets",
        headers=headers,
        json={"weight_kg": "100", "reps": 5, "set_type": "working"},
    )

    finish = await client.post(f"/v1/workout-sessions/{session_id}/finish", headers=headers)
    assert finish.status_code == 200, finish.text

    # Volume: only the working bench set counts (chest 1.00 @ 500 kg). The warm-up
    # rear_delts movement does not appear at all.
    vol = (
        await client.get(
            f"/v1/analytics/volume?from={target.isoformat()}&to={target.isoformat()}",
            headers=headers,
        )
    ).json()["items"]
    by_muscle = {i["muscle"]: i for i in vol}
    chest_pt = next(
        p for p in by_muscle["chest"]["points"] if p["iso_year"] == iy and p["iso_week"] == iw
    )
    assert Decimal(chest_pt["working_sets"]) == Decimal("1.00")
    assert Decimal(chest_pt["tonnage_kg"]) == Decimal("500.00")
    assert "rear_delts" not in by_muscle

    # PRs: the working bench set is a PR; the warm-up movement single is not.
    prs = (await client.get("/v1/me/prs", headers=headers)).json()["items"]
    pr_exercises = {p["exercise_id"] for p in prs}
    assert bench["id"] in pr_exercises
    assert mobility["id"] not in pr_exercises


async def test_cooldown_block_excluded_from_exercise_analytics(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A working set of an exercise builds its series; the same exercise logged in
    a cooldown block on another day must not add a point."""
    headers = await _sign_in(client, monkeypatch, sub="block-ea-sub")
    bench = await _make_exercise(client, headers, name="Bench", primary="chest")
    today = date.today()

    # Working block on day -10.
    s1 = (await client.post("/v1/workout-sessions", headers=headers, json={})).json()["id"]
    await _backdate(s1, today - timedelta(days=10))
    we1 = (
        await client.post(
            f"/v1/workout-sessions/{s1}/exercises",
            headers=headers,
            json={"exercise_id": bench["id"]},
        )
    ).json()
    await client.post(
        f"/v1/workout-exercises/{we1['id']}/sets",
        headers=headers,
        json={"weight_kg": "100", "reps": 5, "set_type": "working"},
    )
    await client.post(f"/v1/workout-sessions/{s1}/finish", headers=headers)

    # Cooldown block on today: must not add a series point.
    s2 = (await client.post("/v1/workout-sessions", headers=headers, json={})).json()["id"]
    await _backdate(s2, today)
    we2 = (
        await client.post(
            f"/v1/workout-sessions/{s2}/exercises",
            headers=headers,
            json={"exercise_id": bench["id"], "block_kind": "cooldown"},
        )
    ).json()
    await client.post(
        f"/v1/workout-exercises/{we2['id']}/sets",
        headers=headers,
        json={"weight_kg": "40", "reps": 12, "set_type": "working"},
    )
    await client.post(f"/v1/workout-sessions/{s2}/finish", headers=headers)

    analytics = (
        await client.get(f"/v1/analytics/exercises/{bench['id']}?window=8w", headers=headers)
    ).json()
    # Exactly one e1RM point: the working-block session only.
    assert len(analytics["e1rm_series"]) == 1
    assert Decimal(analytics["e1rm_series"][0]["value"]) == Decimal("116.67")


# ---------------------------------------------------------------------------
# Segment-summed reps: rest-pause 10+3+2 counts as 15.
# ---------------------------------------------------------------------------


async def test_segment_summed_reps_in_volume_and_pr(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="seg-analytics-sub")
    bench = await _make_exercise(client, headers, name="RP Bench", primary="chest")
    target = _monday(date(2026, 6, 1))
    iy, iw, _ = target.isocalendar()

    session_id = (await client.post("/v1/workout-sessions", headers=headers, json={})).json()["id"]
    await _backdate(session_id, target)
    we = (
        await client.post(
            f"/v1/workout-sessions/{session_id}/exercises",
            headers=headers,
            json={"exercise_id": bench["id"]},
        )
    ).json()
    # A rest-pause set: 10+3+2 at 80 kg. Total reps = 15. The top-level reps is
    # omitted; the segments carry the load.
    await client.post(
        f"/v1/workout-exercises/{we['id']}/sets",
        headers=headers,
        json={
            "set_type": "myo_rep",
            "weight_kg": "80",
            "segments": [
                {"kind": "mini_set", "reps": 10, "weight_kg": "80"},
                {"kind": "rest", "rest_seconds": 15},
                {"kind": "mini_set", "reps": 3, "weight_kg": "80"},
                {"kind": "rest", "rest_seconds": 15},
                {"kind": "mini_set", "reps": 2, "weight_kg": "80"},
            ],
        },
    )
    finish = await client.post(f"/v1/workout-sessions/{session_id}/finish", headers=headers)
    assert finish.status_code == 200, finish.text

    # Tonnage uses summed reps: 80 * 15 = 1200, not 80 * 10.
    vol = (
        await client.get(
            f"/v1/analytics/volume?from={target.isoformat()}&to={target.isoformat()}",
            headers=headers,
        )
    ).json()["items"]
    chest = next(i for i in vol if i["muscle"] == "chest")
    point = next(p for p in chest["points"] if p["iso_year"] == iy and p["iso_week"] == iw)
    assert Decimal(point["working_sets"]) == Decimal("1.00")
    assert Decimal(point["tonnage_kg"]) == Decimal("1200.00")

    # PR e1RM uses 15 reps: 80 * (1 + 15/30) = 120.00.
    prs = (await client.get("/v1/me/prs", headers=headers)).json()["items"]
    bench_prs = [p for p in prs if p["exercise_id"] == bench["id"]]
    assert len(bench_prs) == 1
    assert bench_prs[0]["reps"] == 15
    assert Decimal(bench_prs[0]["e1rm_kg"]) == Decimal("120.00")


# ---------------------------------------------------------------------------
# Skipped sessions are ignored by volume.
# ---------------------------------------------------------------------------


async def test_skipped_session_excluded_from_volume(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="skip-vol-sub")
    bench = await _make_exercise(client, headers, name="Skip Bench", primary="chest")

    program = (
        await client.post(
            "/v1/programs", headers=headers, json={"name": "VolProg", "goal": "general"}
        )
    ).json()
    day = (
        await client.post(
            f"/v1/programs/{program['id']}/slots", headers=headers, json={"name": "Day 1"}
        )
    ).json()
    await client.post(
        f"/v1/program-slots/{day['id']}/exercises",
        headers=headers,
        json={
            "exercise_id": bench["id"],
            "target_sets": 3,
            "target_reps_low": 5,
            "progression_strategy": "linear",
        },
    )
    await client.post(
        f"/v1/programs/{program['id']}/slots",
        headers=headers,
        json={"name": "Rest", "is_rest_day": True},
    )
    await client.post(f"/v1/programs/{program['id']}/activate", headers=headers)
    await seed_scheduled_for_program(program["id"], count=4, start=date.today())

    scheduled = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    workout = (
        await client.post(f"/v1/scheduled-workouts/{scheduled[0]['id']}/start", headers=headers)
    ).json()
    we_id = workout["workout_exercises"][0]["id"]
    await client.post(
        f"/v1/workout-exercises/{we_id}/sets",
        headers=headers,
        json={"weight_kg": "100", "reps": 5, "set_type": "working"},
    )
    # Anchor the session and its scheduled row onto a fixed ISO week.
    target = _monday(date(2026, 6, 8))
    iy, iw, _ = target.isocalendar()
    sm = get_sessionmaker()
    async with sm() as db:
        sched_id = (
            await db.execute(
                select(ScheduledWorkout.id).where(
                    ScheduledWorkout.id == workout["scheduled_workout_id"]
                )
            )
        ).scalar_one()
        await db.execute(
            text("UPDATE workout_sessions SET started_at = :ts WHERE id = :id"),
            {
                "ts": datetime.combine(target, datetime.min.time().replace(hour=12), tzinfo=UTC),
                "id": workout["id"],
            },
        )
        await db.execute(
            text("UPDATE scheduled_workouts SET scheduled_for = :d WHERE id = :id"),
            {"d": target, "id": sched_id},
        )
        await db.commit()

    # Skip it: the partial set is kept on the session but contributes no volume.
    skip = await client.post(f"/v1/workout-sessions/{workout['id']}/skip", headers=headers)
    assert skip.status_code == 200, skip.text

    # Force a recompute of the affected week, then read the rollup.
    from app.services.analytics import volume as volume_svc

    async with sm() as db:
        await volume_svc.rollup_all_users_active_week(db, target)
        await db.commit()

    vol = (
        await client.get(
            f"/v1/analytics/volume?from={target.isoformat()}&to={target.isoformat()}",
            headers=headers,
        )
    ).json()["items"]
    # The skipped session is neutral: no chest volume for that week.
    chest = next((i for i in vol if i["muscle"] == "chest"), None)
    if chest is not None:
        matching = [p for p in chest["points"] if p["iso_year"] == iy and p["iso_week"] == iw]
        assert matching == []
