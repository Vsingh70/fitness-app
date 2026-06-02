"""Tests for the insight TTL cleanup and the PATCH /v1/insights/{id} endpoint.

The TTL tests seed AnalyticsInsight rows directly (backdating created_at via
SQL since created_at uses a server default) and call the pure-ish
``cleanup_expired_insights`` with a pinned ``now``. The PATCH tests drive the
real REST endpoint, reusing the recompute flow to produce a dismissable row.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from app.db import get_sessionmaker
from app.models.analytics_insight import AnalyticsInsight
from app.models.enums import AnalyticsInsightKind, AnalyticsInsightSeverity
from app.models.user import User
from app.services import auth as auth_service
from app.services.analytics import insights as svc

# --- TTL cleanup tests ----------------------------------------------------


async def _make_user(sub: str) -> UUID:
    sm = get_sessionmaker()
    async with sm() as session:
        user = User(apple_sub=sub, email=f"{sub}@example.com")
        session.add(user)
        await session.commit()
        return user.id


async def _make_insight(
    user_id: UUID,
    *,
    kind: AnalyticsInsightKind,
    subject: str,
    created_at: datetime,
    rationale: str | None = None,
    dismissed_at: datetime | None = None,
) -> UUID:
    sm = get_sessionmaker()
    async with sm() as session:
        row = AnalyticsInsight(
            id=uuid4(),
            user_id=user_id,
            kind=kind,
            severity=AnalyticsInsightSeverity.action,
            subject=subject,
            title=f"{subject} insight",
            rationale=rationale,
            dismissed_at=dismissed_at,
        )
        session.add(row)
        await session.flush()
        # created_at has a server default; override it to backdate the row.
        await session.execute(
            text("UPDATE analytics_insights SET created_at = :ts WHERE id = :id"),
            {"ts": created_at, "id": row.id},
        )
        await session.commit()
        return row.id


async def _surviving_ids(user_id: UUID) -> set[UUID]:
    sm = get_sessionmaker()
    async with sm() as session:
        rows = (
            (
                await session.execute(
                    select(AnalyticsInsight.id).where(AnalyticsInsight.user_id == user_id)
                )
            )
            .scalars()
            .all()
        )
        return set(rows)


async def test_cleanup_deletes_old_heuristic_stagnation() -> None:
    """A stagnation insight with no rationale older than 30 days is deleted."""
    now = datetime(2026, 6, 1, tzinfo=UTC)
    user_id = await _make_user("ttl-heuristic")
    old_id = await _make_insight(
        user_id,
        kind=AnalyticsInsightKind.stagnation,
        subject="barbell-deadlift",
        created_at=now - timedelta(days=31),
    )

    sm = get_sessionmaker()
    async with sm() as session:
        deleted = await svc.cleanup_expired_insights(session, now=now)
        await session.commit()

    assert deleted == 1
    assert old_id not in await _surviving_ids(user_id)


async def test_cleanup_keeps_recent_heuristic_stagnation() -> None:
    """A 29-day-old heuristic stagnation insight is just under the TTL: kept."""
    now = datetime(2026, 6, 1, tzinfo=UTC)
    user_id = await _make_user("ttl-recent")
    keep_id = await _make_insight(
        user_id,
        kind=AnalyticsInsightKind.stagnation,
        subject="barbell-squat",
        created_at=now - timedelta(days=29),
    )

    sm = get_sessionmaker()
    async with sm() as session:
        deleted = await svc.cleanup_expired_insights(session, now=now)
        await session.commit()

    assert deleted == 0
    assert keep_id in await _surviving_ids(user_id)


async def test_cleanup_keeps_stagnation_with_llm_rationale() -> None:
    """LLM-rationale stagnation rows survive the 30-day heuristic TTL (they
    only expire after the much longer rationale TTL)."""
    now = datetime(2026, 6, 1, tzinfo=UTC)
    user_id = await _make_user("ttl-rationale")
    keep_id = await _make_insight(
        user_id,
        kind=AnalyticsInsightKind.stagnation,
        subject="barbell-bench-press",
        created_at=now - timedelta(days=120),
        rationale="Your bench has plateaued; try a deload.",
    )

    sm = get_sessionmaker()
    async with sm() as session:
        deleted = await svc.cleanup_expired_insights(session, now=now)
        await session.commit()

    assert deleted == 0
    assert keep_id in await _surviving_ids(user_id)


async def test_cleanup_deletes_very_old_rationale_stagnation() -> None:
    """Beyond the long rationale TTL, even LLM-rationale rows are expired."""
    now = datetime(2026, 6, 1, tzinfo=UTC)
    user_id = await _make_user("ttl-rationale-old")
    old_id = await _make_insight(
        user_id,
        kind=AnalyticsInsightKind.stagnation,
        subject="barbell-row",
        created_at=now - timedelta(days=svc.RATIONALE_TTL_DAYS + 1),
        rationale="Long-stale rationale.",
    )

    sm = get_sessionmaker()
    async with sm() as session:
        deleted = await svc.cleanup_expired_insights(session, now=now)
        await session.commit()

    assert deleted == 1
    assert old_id not in await _surviving_ids(user_id)


async def test_cleanup_ignores_non_stagnation_kinds() -> None:
    """Non-stagnation kinds are NOT subject to the short TTL even when old."""
    now = datetime(2026, 6, 1, tzinfo=UTC)
    user_id = await _make_user("ttl-other-kind")
    keep_id = await _make_insight(
        user_id,
        kind=AnalyticsInsightKind.strong_muscle,
        subject="chest",
        created_at=now - timedelta(days=365),
    )

    sm = get_sessionmaker()
    async with sm() as session:
        deleted = await svc.cleanup_expired_insights(session, now=now)
        await session.commit()

    assert deleted == 0
    assert keep_id in await _surviving_ids(user_id)


# --- PATCH endpoint tests -------------------------------------------------


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _seed_strong_chest(client: AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    await client.patch("/v1/me", headers=headers, json={"sex_at_birth": "male"})
    bench = (
        await client.post(
            "/v1/exercises",
            headers=headers,
            json={
                "name": "Barbell Bench Press",
                "primary_muscle": "chest",
                "secondary_muscles": ["triceps"],
                "equipment": "barbell",
                "movement_pattern": "horizontal_push",
                "tracking_type": "weight_reps",
                "is_unilateral": False,
            },
        )
    ).json()
    target = date.today() - timedelta(days=date.today().weekday())
    session = (await client.post("/v1/workout-sessions", headers=headers, json={})).json()
    sm = get_sessionmaker()
    async with sm() as db:
        await db.execute(
            text(
                "UPDATE workout_sessions SET started_at = :ts, bodyweight_kg = :bw WHERE id = :id"
            ),
            {
                "ts": datetime.combine(target, datetime.min.time().replace(hour=12), tzinfo=UTC),
                "bw": Decimal("80"),
                "id": session["id"],
            },
        )
        await db.commit()
    we = (
        await client.post(
            f"/v1/workout-sessions/{session['id']}/exercises",
            headers=headers,
            json={"exercise_id": bench["id"]},
        )
    ).json()
    await client.post(
        f"/v1/workout-exercises/{we['id']}/sets",
        headers=headers,
        json={"weight_kg": "120", "reps": 5, "set_type": "working"},
    )
    await client.post(f"/v1/workout-sessions/{session['id']}/finish", headers=headers)
    await client.post("/v1/insights/recompute", headers=headers)
    items = (await client.get("/v1/insights", headers=headers)).json()["items"]
    return next(i for i in items if i["kind"] == "strong_muscle" and i["subject"] == "chest")


async def test_patch_dismisses_insight(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="patch-dismiss")
    insight = await _seed_strong_chest(client, headers)
    assert insight["dismissed_at"] is None

    response = await client.patch(
        f"/v1/insights/{insight['id']}", headers=headers, json={"dismissed": True}
    )
    assert response.status_code == 200, response.text
    assert response.json()["dismissed_at"] is not None

    # No longer in the default (active) list.
    active = (await client.get("/v1/insights", headers=headers)).json()["items"]
    assert not any(i["id"] == insight["id"] for i in active)


async def test_patch_undismisses_insight(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="patch-undismiss")
    insight = await _seed_strong_chest(client, headers)

    await client.patch(f"/v1/insights/{insight['id']}", headers=headers, json={"dismissed": True})
    response = await client.patch(
        f"/v1/insights/{insight['id']}", headers=headers, json={"dismissed": False}
    )
    assert response.status_code == 200, response.text
    assert response.json()["dismissed_at"] is None

    active = (await client.get("/v1/insights", headers=headers)).json()["items"]
    assert any(i["id"] == insight["id"] for i in active)


async def test_patch_is_idempotent_keeps_timestamp(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="patch-idempotent")
    insight = await _seed_strong_chest(client, headers)

    first = await client.patch(
        f"/v1/insights/{insight['id']}", headers=headers, json={"dismissed": True}
    )
    first_ts = first.json()["dismissed_at"]
    second = await client.patch(
        f"/v1/insights/{insight['id']}", headers=headers, json={"dismissed": True}
    )
    assert second.json()["dismissed_at"] == first_ts


async def test_patch_unknown_insight_returns_404(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch, sub="patch-404")
    response = await client.patch(
        f"/v1/insights/{uuid4()}", headers=headers, json={"dismissed": True}
    )
    assert response.status_code == 404


async def test_patch_other_users_insight_returns_404(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await _sign_in(client, monkeypatch, sub="patch-owner")
    insight = await _seed_strong_chest(client, owner)

    intruder = await _sign_in(client, monkeypatch, sub="patch-intruder")
    response = await client.patch(
        f"/v1/insights/{insight['id']}", headers=intruder, json={"dismissed": True}
    )
    assert response.status_code == 404
