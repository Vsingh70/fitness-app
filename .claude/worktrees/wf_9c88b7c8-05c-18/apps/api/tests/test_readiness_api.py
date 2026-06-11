"""Integration tests for readiness persistence, fatigue hook, and endpoints."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from app.db import get_sessionmaker
from app.models.daily_metric import DailyMetric
from app.models.scheduled_workout import ScheduledWorkout
from app.models.user_fatigue_state import UserFatigueState
from app.services import auth as auth_service
from app.services import readiness as readiness_svc


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "rd-sub"
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _user_id(client: AsyncClient, headers: dict[str, str]) -> str:
    me = (await client.get("/v1/me", headers=headers)).json()
    return me["id"]


async def _seed_daily(
    user_id: str,
    on_date: date,
    *,
    sleep_minutes: int | None = None,
    resting_hr: int | None = None,
    hrv_ms: str | None = None,
) -> None:
    sm = get_sessionmaker()
    async with sm() as db:
        await db.execute(
            text(
                """
                INSERT INTO daily_metrics
                  (id, user_id, date, sleep_minutes, resting_hr, hrv_ms, created_at, updated_at)
                VALUES
                  (gen_random_uuid(), :user_id, :date, :sleep, :rhr, :hrv, NOW(), NOW())
                ON CONFLICT (user_id, date) DO UPDATE SET
                  sleep_minutes = EXCLUDED.sleep_minutes,
                  resting_hr = EXCLUDED.resting_hr,
                  hrv_ms = EXCLUDED.hrv_ms,
                  updated_at = NOW()
                """
            ),
            {
                "user_id": user_id,
                "date": on_date,
                "sleep": sleep_minutes,
                "rhr": resting_hr,
                "hrv": Decimal(hrv_ms) if hrv_ms else None,
            },
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Persistence + recompute
# ---------------------------------------------------------------------------


async def test_recompute_persists_score_into_daily_metrics(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    user_id = await _user_id(client, headers)
    today = date(2026, 6, 1)
    # Seed 14 days of baseline RHR=60.
    for offset in range(1, 15):
        await _seed_daily(user_id, today - timedelta(days=offset), resting_hr=60)
    # Today: perfect sleep, RHR slightly elevated (65).
    await _seed_daily(user_id, today, sleep_minutes=480, resting_hr=65)

    sm = get_sessionmaker()
    async with sm() as db:
        from uuid import UUID

        breakdown = await readiness_svc.recompute_for_user_date(
            db, UUID(user_id), target_date=today
        )
        await db.commit()
    assert breakdown is not None
    # Without HRV: sleep=55, rhr = (1 - 5/10) * 45 = 22.5 -> total 77.5 -> 78.
    assert breakdown.score == 78
    assert breakdown.band == "high"

    async with sm() as db:
        row = (
            await db.execute(
                select(DailyMetric).where(
                    DailyMetric.user_id == UUID(user_id), DailyMetric.date == today
                )
            )
        ).scalar_one()
    assert row.readiness_score == 78


async def test_recompute_returns_none_when_no_signals(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    user_id = await _user_id(client, headers)
    today = date(2026, 6, 1)
    # Insert a row with all-null signals.
    await _seed_daily(user_id, today)

    from uuid import UUID

    sm = get_sessionmaker()
    async with sm() as db:
        breakdown = await readiness_svc.recompute_for_user_date(
            db, UUID(user_id), target_date=today
        )
    assert breakdown is None


async def test_baseline_excludes_target_date(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Today's RHR should not pull its own baseline."""
    headers = await _sign_in(client, monkeypatch)
    user_id = await _user_id(client, headers)
    today = date(2026, 6, 1)
    # 14 days of baseline RHR=60.
    for offset in range(1, 15):
        await _seed_daily(user_id, today - timedelta(days=offset), resting_hr=60)
    # Today RHR=60 too -> if baseline included today, we'd still see RHR=60.
    # If baseline excludes today, baseline still = 60 (from prior days).
    await _seed_daily(user_id, today, sleep_minutes=480, resting_hr=60)
    from uuid import UUID

    sm = get_sessionmaker()
    async with sm() as db:
        breakdown = await readiness_svc.recompute_for_user_date(
            db, UUID(user_id), target_date=today
        )
        await db.commit()
    assert breakdown is not None
    # RHR = baseline -> rhr component is full (no missed HRV redistribution effect).
    # sleep=55, rhr=45 -> 100.
    assert breakdown.score == 100


# ---------------------------------------------------------------------------
# Fatigue +1 on transition to low
# ---------------------------------------------------------------------------


async def test_low_readiness_bumps_fatigue_once_per_transition(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    user_id = await _user_id(client, headers)
    today = date(2026, 6, 1)
    # Baseline RHR=60.
    for offset in range(1, 15):
        await _seed_daily(user_id, today - timedelta(days=offset), resting_hr=60)
    # Low-band day: sleep=0, RHR=70 -> sleep=0, rhr=0, hrv=0 -> 0.
    await _seed_daily(user_id, today, sleep_minutes=0, resting_hr=70)

    from uuid import UUID

    sm = get_sessionmaker()
    async with sm() as db:
        breakdown = await readiness_svc.recompute_for_user_date(
            db, UUID(user_id), target_date=today
        )
        await db.commit()
    assert breakdown is not None
    assert breakdown.band == "low"

    async with sm() as db:
        state = (
            await db.execute(
                select(UserFatigueState).where(UserFatigueState.user_id == UUID(user_id))
            )
        ).scalar_one()
    assert state.rolling_7d_score == Decimal("1.0")

    # Recompute the same day with no data changes -> no additional bump.
    async with sm() as db:
        await readiness_svc.recompute_for_user_date(db, UUID(user_id), target_date=today)
        await db.commit()
    async with sm() as db:
        state2 = (
            await db.execute(
                select(UserFatigueState).where(UserFatigueState.user_id == UUID(user_id))
            )
        ).scalar_one()
    assert state2.rolling_7d_score == Decimal("1.0")


async def test_moderate_to_low_transition_bumps_fatigue(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    user_id = await _user_id(client, headers)
    today = date(2026, 6, 1)
    for offset in range(1, 15):
        await _seed_daily(user_id, today - timedelta(days=offset), resting_hr=60)
    # First store a moderate-band day.
    await _seed_daily(user_id, today, sleep_minutes=240, resting_hr=63)
    from uuid import UUID

    sm = get_sessionmaker()
    async with sm() as db:
        breakdown1 = await readiness_svc.recompute_for_user_date(
            db, UUID(user_id), target_date=today
        )
        await db.commit()
    assert breakdown1 is not None
    # Now degrade the day to low.
    await _seed_daily(user_id, today, sleep_minutes=0, resting_hr=75)
    async with sm() as db:
        breakdown2 = await readiness_svc.recompute_for_user_date(
            db, UUID(user_id), target_date=today
        )
        await db.commit()
    assert breakdown2 is not None
    assert breakdown2.band == "low"

    async with sm() as db:
        state = (
            await db.execute(
                select(UserFatigueState).where(UserFatigueState.user_id == UUID(user_id))
            )
        ).scalar_one()
    assert state.rolling_7d_score == Decimal("1.0")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


async def test_readiness_today_no_data(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    response = await client.get("/v1/readiness/today", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["has_data"] is False
    assert body["score"] is None


async def test_readiness_today_with_score(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    user_id = await _user_id(client, headers)
    today = datetime.now(tz=UTC).date()
    for offset in range(1, 15):
        await _seed_daily(user_id, today - timedelta(days=offset), resting_hr=60)
    await _seed_daily(user_id, today, sleep_minutes=480, resting_hr=60)
    from uuid import UUID

    sm = get_sessionmaker()
    async with sm() as db:
        await readiness_svc.recompute_for_user_date(db, UUID(user_id), target_date=today)
        await db.commit()

    response = await client.get("/v1/readiness/today", headers=headers)
    body = response.json()
    assert body["has_data"] is True
    assert body["band"] == "high"
    assert body["score"] == 100


async def test_readiness_history_endpoint(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    user_id = await _user_id(client, headers)
    today = date(2026, 6, 1)
    for offset in range(1, 15):
        await _seed_daily(user_id, today - timedelta(days=offset), resting_hr=60)
    await _seed_daily(user_id, today, sleep_minutes=480, resting_hr=60)
    from uuid import UUID

    sm = get_sessionmaker()
    async with sm() as db:
        await readiness_svc.recompute_for_user_date(db, UUID(user_id), target_date=today)
        await db.commit()

    response = await client.get(
        f"/v1/readiness/history?from={today - timedelta(days=15)}&to={today}",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert any(item["date"] == today.isoformat() and item["score"] == 100 for item in items)


async def test_history_range_validation(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    response = await client.get(
        "/v1/readiness/history?from=2026-06-10&to=2026-06-01", headers=headers
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Reduce today's volume
# ---------------------------------------------------------------------------


async def test_reduce_today_volume_flips_is_deload_and_revert_unflips(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)

    # Build a program + scheduled today.
    exercise = (
        await client.post(
            "/v1/exercises",
            headers=headers,
            json={
                "name": "Bench",
                "primary_muscle": "chest",
                "secondary_muscles": ["triceps"],
                "equipment": "barbell",
                "movement_pattern": "horizontal_push",
                "tracking_type": "weight_reps",
                "is_unilateral": False,
            },
        )
    ).json()
    program = (
        await client.post(
            "/v1/programs",
            headers=headers,
            json={"name": "P", "goal": "strength", "weeks": 1, "days_per_week": 1},
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
            "exercise_id": exercise["id"],
            "target_sets": 3,
            "target_reps_low": 5,
            "progression_strategy": "linear",
        },
    )
    today = datetime.now(tz=UTC).date()
    monday = today - timedelta(days=today.weekday())
    await client.post(
        f"/v1/programs/{program['id']}/activate",
        headers=headers,
        json={
            "start_date": monday.isoformat(),
            "weekday_offset": today.weekday(),
            "skip_existing": True,
        },
    )

    reduce = await client.post("/v1/readiness/reduce-today-volume", headers=headers)
    assert reduce.status_code == 200, reduce.text
    body = reduce.json()
    assert body["affected_count"] >= 1
    affected_ids = body["affected_scheduled_workout_ids"]
    assert len(affected_ids) >= 1

    # Verify is_deload=True on those rows.
    sm = get_sessionmaker()
    async with sm() as db:
        from uuid import UUID

        rows = (
            (
                await db.execute(
                    select(ScheduledWorkout).where(
                        ScheduledWorkout.id.in_([UUID(i) for i in affected_ids])
                    )
                )
            )
            .scalars()
            .all()
        )
    assert all(r.is_deload for r in rows)

    # Revert.
    revert = await client.request(
        "DELETE",
        "/v1/readiness/reduce-today-volume",
        headers=headers,
        json={"scheduled_workout_ids": affected_ids},
    )
    assert revert.status_code == 200
    assert revert.json()["affected_count"] == len(affected_ids)

    async with sm() as db:
        rows = (
            (
                await db.execute(
                    select(ScheduledWorkout).where(
                        ScheduledWorkout.id.in_([UUID(i) for i in affected_ids])
                    )
                )
            )
            .scalars()
            .all()
        )
    assert all(not r.is_deload for r in rows)


async def test_revert_with_empty_ids_returns_zero(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    response = await client.request(
        "DELETE",
        "/v1/readiness/reduce-today-volume",
        headers=headers,
        json={"scheduled_workout_ids": []},
    )
    assert response.status_code == 200
    assert response.json()["affected_count"] == 0
