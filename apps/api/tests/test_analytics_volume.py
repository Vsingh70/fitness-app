"""End-to-end tests for per-muscle weekly volume rollup.

A "hand-counted" fixture builds a small but exhaustive scenario and asserts on
the rollup output via the GET /v1/analytics/volume endpoint.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.db import get_sessionmaker
from app.services import auth as auth_service


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "vol-sub"
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
    primary: str,
    secondary: list[str],
    tracking_type: str = "weight_reps",
) -> dict[str, Any]:
    payload = {
        "name": name,
        "primary_muscle": primary,
        "secondary_muscles": secondary,
        "equipment": "barbell",
        "movement_pattern": "horizontal_push",
        "tracking_type": tracking_type,
        "is_unilateral": False,
    }
    return (await client.post("/v1/exercises", headers=headers, json=payload)).json()


async def _log_session_on_date(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    on_date: date,
    exercises: list[dict[str, Any]],
    bodyweight_kg: str | None = None,
) -> str:
    """Create a free-style session, set started_at to noon on `on_date`, log
    sets, finish. Returns the session id.
    """
    session = (await client.post("/v1/workout-sessions", headers=headers, json={})).json()
    # Reach into the DB to backdate started_at to the target date.
    sm = get_sessionmaker()
    async with sm() as db:
        await db.execute(
            text(
                "UPDATE workout_sessions SET started_at = :ts, bodyweight_kg = :bw WHERE id = :id"
            ),
            {
                "ts": datetime.combine(on_date, datetime.min.time().replace(hour=12), tzinfo=UTC),
                "bw": Decimal(bodyweight_kg) if bodyweight_kg is not None else None,
                "id": session["id"],
            },
        )
        await db.commit()
    for ex in exercises:
        we = (
            await client.post(
                f"/v1/workout-sessions/{session['id']}/exercises",
                headers=headers,
                json={"exercise_id": ex["exercise_id"]},
            )
        ).json()
        for s in ex["sets"]:
            await client.post(
                f"/v1/workout-exercises/{we['id']}/sets",
                headers=headers,
                json={
                    "weight_kg": s.get("weight_kg"),
                    "reps": s.get("reps"),
                    "rir": s.get("rir"),
                    "set_type": s.get("set_type", "working"),
                },
            )
    finish = await client.post(f"/v1/workout-sessions/{session['id']}/finish", headers=headers)
    assert finish.status_code == 200, finish.text
    return session["id"]


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


# ---------------------------------------------------------------------------
# Hand-counted scenario
# ---------------------------------------------------------------------------
#
# Two exercises:
#   Bench: primary=chest, secondary=[triceps, front_delts]
#   Row:   primary=lats,  secondary=[biceps, rear_delts]
#
# Three sessions in one ISO week:
#   Session A: Bench 3x5 @ 100 kg, RIR=2 each
#   Session B: Bench 1 warmup set (excluded), then 2 working sets 5 @ 100 kg, RIR=1
#   Session C: Row 4x8 @ 80 kg, RIR=3
#
# Expected (per ISO week):
#   chest:      working_sets = 3 (sess A primary) + 2 (sess B primary) = 5.00
#               tonnage      = 3*100*5 + 2*100*5                       = 2500.00
#               average_rir  = avg(2,2,2,1,1)                          = 1.60
#   triceps:    0.5*3 + 0.5*2 = 2.50, tonnage 0.5*1500 + 0.5*1000 = 1250.00,
#               rir avg over 5 sets = 1.60
#   front_delts: same as triceps
#   lats:       4.00, tonnage 4*80*8 = 2560.00, rir avg = 3.00
#   biceps:     2.00, tonnage 0.5*2560 = 1280.00, rir avg = 3.00
#   rear_delts: same as biceps


async def test_hand_counted_rollup_matches(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    bench = await _make_exercise(
        client, headers, name="Bench", primary="chest", secondary=["triceps", "front_delts"]
    )
    row = await _make_exercise(
        client, headers, name="Row", primary="lats", secondary=["biceps", "rear_delts"]
    )

    target_monday = _monday(date(2026, 6, 1))  # ISO week 23 of 2026
    expected_iy, expected_iw, _ = target_monday.isocalendar()

    # Session A: Bench 3x5 @ 100, RIR=2
    await _log_session_on_date(
        client,
        headers,
        on_date=target_monday,
        exercises=[
            {
                "exercise_id": bench["id"],
                "sets": [{"weight_kg": "100", "reps": 5, "rir": 2} for _ in range(3)],
            }
        ],
    )
    # Session B: Bench 1 warmup + 2 working sets 5 @ 100, RIR=1
    await _log_session_on_date(
        client,
        headers,
        on_date=target_monday + timedelta(days=2),
        exercises=[
            {
                "exercise_id": bench["id"],
                "sets": [
                    {"weight_kg": "60", "reps": 5, "rir": 4, "set_type": "warmup"},
                    {"weight_kg": "100", "reps": 5, "rir": 1, "set_type": "working"},
                    {"weight_kg": "100", "reps": 5, "rir": 1, "set_type": "working"},
                ],
            }
        ],
    )
    # Session C: Row 4x8 @ 80, RIR=3
    await _log_session_on_date(
        client,
        headers,
        on_date=target_monday + timedelta(days=4),
        exercises=[
            {
                "exercise_id": row["id"],
                "sets": [{"weight_kg": "80", "reps": 8, "rir": 3} for _ in range(4)],
            }
        ],
    )

    # Read the persisted rollup.
    from_iso = (target_monday - timedelta(days=1)).isoformat()
    to_iso = (target_monday + timedelta(days=7)).isoformat()
    response = await client.get(
        f"/v1/analytics/volume?from={from_iso}&to={to_iso}", headers=headers
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    by_muscle = {item["muscle"]: item for item in items}

    def _point(name: str) -> dict[str, Any]:
        points = by_muscle[name]["points"]
        match = [p for p in points if p["iso_year"] == expected_iy and p["iso_week"] == expected_iw]
        assert len(match) == 1, f"expected one point for {name}, got {match}"
        return match[0]

    chest = _point("chest")
    assert Decimal(chest["working_sets"]) == Decimal("5.00")
    assert Decimal(chest["tonnage_kg"]) == Decimal("2500.00")
    assert Decimal(chest["average_rir"]) == Decimal("1.60")

    triceps = _point("triceps")
    assert Decimal(triceps["working_sets"]) == Decimal("2.50")
    assert Decimal(triceps["tonnage_kg"]) == Decimal("1250.00")

    front_delts = _point("front_delts")
    assert Decimal(front_delts["working_sets"]) == Decimal("2.50")
    assert Decimal(front_delts["tonnage_kg"]) == Decimal("1250.00")

    lats = _point("lats")
    assert Decimal(lats["working_sets"]) == Decimal("4.00")
    assert Decimal(lats["tonnage_kg"]) == Decimal("2560.00")
    assert Decimal(lats["average_rir"]) == Decimal("3.00")

    biceps = _point("biceps")
    assert Decimal(biceps["working_sets"]) == Decimal("2.00")
    assert Decimal(biceps["tonnage_kg"]) == Decimal("1280.00")

    rear_delts = _point("rear_delts")
    assert Decimal(rear_delts["working_sets"]) == Decimal("2.00")
    assert Decimal(rear_delts["tonnage_kg"]) == Decimal("1280.00")


async def test_warmup_sets_are_excluded(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    bench = await _make_exercise(client, headers, name="Bench", primary="chest", secondary=[])
    target = _monday(date(2026, 6, 1))
    iy, iw, _ = target.isocalendar()
    await _log_session_on_date(
        client,
        headers,
        on_date=target,
        exercises=[
            {
                "exercise_id": bench["id"],
                "sets": [
                    {"weight_kg": "60", "reps": 10, "set_type": "warmup"},
                    {"weight_kg": "100", "reps": 5, "set_type": "working"},
                ],
            }
        ],
    )
    response = await client.get(
        f"/v1/analytics/volume?from={target.isoformat()}&to={target.isoformat()}",
        headers=headers,
    )
    items = response.json()["items"]
    chest = next(i for i in items if i["muscle"] == "chest")
    point = next(p for p in chest["points"] if p["iso_year"] == iy and p["iso_week"] == iw)
    assert Decimal(point["working_sets"]) == Decimal("1.00")
    assert Decimal(point["tonnage_kg"]) == Decimal("500.00")


async def test_bodyweight_only_session_uses_session_bw_for_tonnage(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    pullup = await _make_exercise(
        client,
        headers,
        name="Pull-up",
        primary="lats",
        secondary=["biceps"],
        tracking_type="bodyweight_reps",
    )
    target = _monday(date(2026, 6, 1))
    iy, iw, _ = target.isocalendar()
    await _log_session_on_date(
        client,
        headers,
        on_date=target,
        bodyweight_kg="80",
        exercises=[
            {
                "exercise_id": pullup["id"],
                "sets": [{"weight_kg": None, "reps": 10, "set_type": "working"} for _ in range(3)],
            }
        ],
    )
    response = await client.get(
        f"/v1/analytics/volume?from={target.isoformat()}&to={target.isoformat()}",
        headers=headers,
    )
    items = response.json()["items"]
    lats = next(i for i in items if i["muscle"] == "lats")
    point = next(p for p in lats["points"] if p["iso_year"] == iy and p["iso_week"] == iw)
    # 3 working sets of bodyweight 80 kg * 10 reps = 2400 kg.
    assert Decimal(point["working_sets"]) == Decimal("3.00")
    assert Decimal(point["tonnage_kg"]) == Decimal("2400.00")


async def test_editing_a_set_after_finish_triggers_recompute(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    bench = await _make_exercise(client, headers, name="Bench", primary="chest", secondary=[])
    target = _monday(date(2026, 6, 1))
    iy, iw, _ = target.isocalendar()
    await _log_session_on_date(
        client,
        headers,
        on_date=target,
        exercises=[
            {
                "exercise_id": bench["id"],
                "sets": [{"weight_kg": "100", "reps": 5, "set_type": "working"}],
            }
        ],
    )
    response = await client.get(
        f"/v1/analytics/volume?from={target.isoformat()}&to={target.isoformat()}",
        headers=headers,
    )
    chest = next(i for i in response.json()["items"] if i["muscle"] == "chest")
    point = next(p for p in chest["points"] if p["iso_year"] == iy and p["iso_week"] == iw)
    assert Decimal(point["tonnage_kg"]) == Decimal("500.00")

    # Find the set and patch reps from 5 -> 8.
    sm = get_sessionmaker()
    async with sm() as db:
        set_id = (
            await db.execute(text("SELECT id FROM sets ORDER BY created_at LIMIT 1"))
        ).scalar_one()
    patch = await client.patch(f"/v1/sets/{set_id}", headers=headers, json={"reps": 8})
    assert patch.status_code == 200, patch.text

    # Rollup should now reflect 100 * 8 = 800.
    response = await client.get(
        f"/v1/analytics/volume?from={target.isoformat()}&to={target.isoformat()}",
        headers=headers,
    )
    chest = next(i for i in response.json()["items"] if i["muscle"] == "chest")
    point = next(p for p in chest["points"] if p["iso_year"] == iy and p["iso_week"] == iw)
    assert Decimal(point["tonnage_kg"]) == Decimal("800.00")


async def test_current_week_endpoint(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """The /current-week endpoint returns a per-muscle summary for today's
    ISO week. We anchor on today's date so the test is independent of fixture
    dates.
    """
    headers = await _sign_in(client, monkeypatch)
    bench = await _make_exercise(
        client, headers, name="Bench", primary="chest", secondary=["triceps"]
    )
    today = datetime.now(tz=UTC).date()
    await _log_session_on_date(
        client,
        headers,
        on_date=today,
        exercises=[
            {
                "exercise_id": bench["id"],
                "sets": [{"weight_kg": "100", "reps": 5, "set_type": "working"} for _ in range(3)],
            }
        ],
    )
    response = await client.get("/v1/analytics/volume/current-week", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    iy, iw, _ = today.isocalendar()
    assert data["iso_year"] == iy
    assert data["iso_week"] == iw
    assert Decimal(data["total_working_sets"]) == Decimal("4.50")  # 3 chest + 1.5 triceps
    assert Decimal(data["total_tonnage_kg"]) == Decimal("2250.00")  # 1500 + 750


async def test_volume_range_validation(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    # to < from
    response = await client.get(
        "/v1/analytics/volume?from=2026-06-01&to=2026-05-01", headers=headers
    )
    assert response.status_code == 400
    # Range too large: 52 weeks * 7 days + 1
    response = await client.get(
        "/v1/analytics/volume?from=2025-01-01&to=2026-06-01", headers=headers
    )
    assert response.status_code == 400
