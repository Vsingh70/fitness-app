from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db import get_sessionmaker
from app.models.notification import Notification
from app.models.user import User
from app.services import auth as auth_service
from app.services.scheduling import enqueue_workout_reminders
from scripts.seed_exercises import seed as seed_exercises


async def _sign_in(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    sub: str = "sched-sub",
) -> tuple[dict[str, str], str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    body = response.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, sub


async def _create_4day_program_with_days(
    client: AsyncClient, headers: dict[str, str], exercise_id: str | None = None
) -> str:
    program = (
        await client.post(
            "/v1/programs",
            headers=headers,
            json={
                "name": "Sched Test",
                "goal": "general",
                "weeks": 4,
                "days_per_week": 4,
            },
        )
    ).json()
    for name in ["Push A", "Pull A", "Push B", "Pull B"]:
        day = (
            await client.post(
                f"/v1/programs/{program['id']}/days",
                headers=headers,
                json={"name": name},
            )
        ).json()
        if exercise_id is not None:
            await client.post(
                f"/v1/program-days/{day['id']}/exercises",
                headers=headers,
                json={
                    "exercise_id": exercise_id,
                    "target_sets": 3,
                    "progression_strategy": "none",
                },
            )
    return program["id"]


async def _activate(
    client: AsyncClient,
    headers: dict[str, str],
    program_id: str,
    *,
    start_date: str = "2026-06-01",
    weekday_offset: int = 0,
) -> None:
    response = await client.post(
        f"/v1/programs/{program_id}/activate",
        headers=headers,
        json={
            "start_date": start_date,
            "weekday_offset": weekday_offset,
            "skip_existing": True,
        },
    )
    assert response.status_code == 200, response.text


# ---------------------------------------------------------------------------
# List + filter
# ---------------------------------------------------------------------------


async def test_list_scheduled_after_activate(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, _ = await _sign_in(client, monkeypatch)
    program_id = await _create_4day_program_with_days(client, headers)
    await _activate(client, headers, program_id)

    response = await client.get("/v1/scheduled-workouts", headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 16  # 4 weeks * 4 days
    # Status all planned. With default meso_length=4 over 4 weeks, week 4
    # is a taper-deload; weeks 1-3 are normal.
    for item in items:
        assert item["status"] == "planned"
    deload_flags = [item["is_deload"] for item in items]
    # First 12 (weeks 1-3, 4 days each) are normal; final 4 (week 4) are deload.
    assert deload_flags == [False] * 12 + [True] * 4
    # Sorted ascending by date.
    dates = [item["scheduled_for"] for item in items]
    assert dates == sorted(dates)


async def test_list_scheduled_filters_by_range(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, _ = await _sign_in(client, monkeypatch)
    program_id = await _create_4day_program_with_days(client, headers)
    await _activate(client, headers, program_id)

    response = await client.get(
        "/v1/scheduled-workouts?from=2026-06-08&to=2026-06-14",
        headers=headers,
    )
    items = response.json()["items"]
    assert len(items) == 4  # week 2 only
    for item in items:
        assert "2026-06-08" <= item["scheduled_for"] <= "2026-06-14"


# ---------------------------------------------------------------------------
# Reschedule (single + cascade)
# ---------------------------------------------------------------------------


async def test_patch_single_reschedule(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, _ = await _sign_in(client, monkeypatch)
    program_id = await _create_4day_program_with_days(client, headers)
    await _activate(client, headers, program_id)
    items = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    target = items[0]
    original_date = target["scheduled_for"]
    new_date = (date.fromisoformat(original_date) + timedelta(days=2)).isoformat()

    patch = await client.patch(
        f"/v1/scheduled-workouts/{target['id']}",
        headers=headers,
        json={"scheduled_for": new_date},
    )
    assert patch.status_code == 200
    assert patch.json()["scheduled_for"] == new_date

    # No other rows moved.
    after = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    others_after = [a["scheduled_for"] for a in after if a["id"] != target["id"]]
    others_before = [b["scheduled_for"] for b in items if b["id"] != target["id"]]
    assert sorted(others_after) == sorted(others_before)


async def test_patch_with_shift_cascades_remaining(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, _ = await _sign_in(client, monkeypatch)
    program_id = await _create_4day_program_with_days(client, headers)
    await _activate(client, headers, program_id)
    items = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    # Pick the 5th row (week 2 day 1); shift its scheduled_for forward 3 days
    # and cascade. Rows 6..16 (every row strictly after this date) should shift.
    target = items[4]
    original = date.fromisoformat(target["scheduled_for"])
    new_date = (original + timedelta(days=3)).isoformat()

    patch = await client.patch(
        f"/v1/scheduled-workouts/{target['id']}?shift_remaining_days=3",
        headers=headers,
        json={"scheduled_for": new_date},
    )
    assert patch.status_code == 200

    after = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    after_by_id = {a["id"]: a for a in after}

    # Target moved to new_date.
    assert after_by_id[target["id"]]["scheduled_for"] == new_date
    # Every row that was originally > target's original date shifted by +3.
    for before in items:
        if before["id"] == target["id"]:
            continue
        before_date = date.fromisoformat(before["scheduled_for"])
        if before_date > original:
            expected = (before_date + timedelta(days=3)).isoformat()
            assert after_by_id[before["id"]]["scheduled_for"] == expected
        else:
            assert after_by_id[before["id"]]["scheduled_for"] == before["scheduled_for"]


# ---------------------------------------------------------------------------
# Skip / unskip
# ---------------------------------------------------------------------------


async def test_skip_then_unskip(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    headers, _ = await _sign_in(client, monkeypatch)
    program_id = await _create_4day_program_with_days(client, headers)
    await _activate(client, headers, program_id)
    target = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"][0]

    skip = await client.patch(
        f"/v1/scheduled-workouts/{target['id']}",
        headers=headers,
        json={"status": "skipped"},
    )
    assert skip.status_code == 200
    assert skip.json()["status"] == "skipped"

    unskip = await client.patch(
        f"/v1/scheduled-workouts/{target['id']}",
        headers=headers,
        json={"status": "planned"},
    )
    assert unskip.status_code == 200
    assert unskip.json()["status"] == "planned"


# ---------------------------------------------------------------------------
# Start from scheduled (pre-populates exercises) + auto-complete on finish
# ---------------------------------------------------------------------------


async def test_start_session_pre_populates_exercises(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed_exercises()
    headers, _ = await _sign_in(client, monkeypatch)
    exercise = (await client.get("/v1/exercises?limit=1", headers=headers)).json()["items"][0]
    program_id = await _create_4day_program_with_days(client, headers, exercise_id=exercise["id"])
    await _activate(client, headers, program_id)
    target = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"][0]

    start = await client.post(f"/v1/scheduled-workouts/{target['id']}/start", headers=headers)
    assert start.status_code == 201, start.text
    workout = start.json()
    assert len(workout["workout_exercises"]) == 1
    assert workout["workout_exercises"][0]["exercise_id"] == exercise["id"]

    # Scheduled status flipped to in_progress.
    items = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    by_id = {i["id"]: i for i in items}
    assert by_id[target["id"]]["status"] == "in_progress"


async def test_finish_session_marks_scheduled_completed(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed_exercises()
    headers, _ = await _sign_in(client, monkeypatch)
    exercise = (await client.get("/v1/exercises?limit=1", headers=headers)).json()["items"][0]
    program_id = await _create_4day_program_with_days(client, headers, exercise_id=exercise["id"])
    await _activate(client, headers, program_id)
    target = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"][0]
    workout = (
        await client.post(f"/v1/scheduled-workouts/{target['id']}/start", headers=headers)
    ).json()

    finish = await client.post(f"/v1/workout-sessions/{workout['id']}/finish", headers=headers)
    assert finish.status_code == 200

    after = (await client.get("/v1/scheduled-workouts", headers=headers)).json()["items"]
    by_id = {i["id"]: i for i in after}
    assert by_id[target["id"]]["status"] == "completed"


# ---------------------------------------------------------------------------
# Reminder job
# ---------------------------------------------------------------------------


async def test_reminder_job_inserts_only_for_users_at_six_am(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, sub = await _sign_in(client, monkeypatch, sub="rem-sub")
    program_id = await _create_4day_program_with_days(client, headers)

    # Find the user's id and lock their timezone so we can deterministically
    # construct a "now" that is 06:00 in their tz.
    sm = get_sessionmaker()
    async with sm() as session:
        user = (await session.execute(select(User).where(User.apple_sub == sub))).scalar_one()
        user.timezone = "UTC"
        await session.commit()
        user_id = user.id

    # Pick a date that the activation will schedule on (Monday in UTC).
    target_date = date(2026, 6, 1)  # Monday
    await _activate(
        client,
        headers,
        program_id,
        start_date=target_date.isoformat(),
        weekday_offset=0,
    )

    six_utc = datetime(target_date.year, target_date.month, target_date.day, 6, 0, tzinfo=UTC)
    sm = get_sessionmaker()
    async with sm() as session:
        inserted = await enqueue_workout_reminders(session, now_utc=six_utc)
        await session.commit()
    assert inserted == 1

    async with sm() as session:
        notifications = (
            (await session.execute(select(Notification).where(Notification.user_id == user_id)))
            .scalars()
            .all()
        )
    assert len(notifications) == 1
    assert notifications[0].kind.value == "workout_reminder"
    payload = notifications[0].payload
    assert payload["date"] == target_date.isoformat()
    assert isinstance(payload["scheduled_workout_ids"], list)
    assert len(payload["scheduled_workout_ids"]) > 0


async def test_reminder_job_idempotent_within_hour(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, sub = await _sign_in(client, monkeypatch, sub="rem-idem")
    program_id = await _create_4day_program_with_days(client, headers)
    sm = get_sessionmaker()
    async with sm() as session:
        user = (await session.execute(select(User).where(User.apple_sub == sub))).scalar_one()
        user.timezone = "UTC"
        await session.commit()

    target_date = date(2026, 6, 1)
    await _activate(
        client,
        headers,
        program_id,
        start_date=target_date.isoformat(),
        weekday_offset=0,
    )
    six_utc = datetime(target_date.year, target_date.month, target_date.day, 6, 0, tzinfo=UTC)

    sm = get_sessionmaker()
    async with sm() as session:
        first = await enqueue_workout_reminders(session, now_utc=six_utc)
        await session.commit()
        second = await enqueue_workout_reminders(session, now_utc=six_utc)
        await session.commit()
    assert first == 1
    assert second == 0


async def test_reminder_job_skips_users_outside_six_am(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, sub = await _sign_in(client, monkeypatch, sub="rem-noon")
    program_id = await _create_4day_program_with_days(client, headers)
    sm = get_sessionmaker()
    async with sm() as session:
        user = (await session.execute(select(User).where(User.apple_sub == sub))).scalar_one()
        user.timezone = "UTC"
        await session.commit()
    await _activate(
        client,
        headers,
        program_id,
        start_date="2026-06-01",
        weekday_offset=0,
    )
    noon_utc = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    sm = get_sessionmaker()
    async with sm() as session:
        count = await enqueue_workout_reminders(session, now_utc=noon_utc)
    assert count == 0
