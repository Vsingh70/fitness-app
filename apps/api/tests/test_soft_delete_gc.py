"""Tests for the nightly soft-delete garbage-collection job.

Seeds, for each soft-deletable table, one row deleted long ago (eligible) and
one deleted recently (spared), plus a live row, then asserts the purge job
deletes only the stale soft-deleted rows and bumps the Prometheus counter.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select

from app.db import get_sessionmaker
from app.models.enums import MealType, ProgramGoal, ProgramSource
from app.models.meal import Meal
from app.models.program import Program
from app.models.user import User
from app.models.workout import WorkoutSession
from app.observability.metrics import SOFT_DELETE_PURGED_TOTAL
from app.services.soft_delete_gc import RETENTION_DAYS, purge_soft_deleted


def _counter_value(table: str) -> float:
    for metric in SOFT_DELETE_PURGED_TOTAL.collect():
        for sample in metric.samples:
            if sample.labels.get("table") == table and sample.name.endswith("_total"):
                return sample.value
    return 0.0


async def _make_user(session) -> UUID:
    user = User(email="gc@example.com", apple_sub="gc-sub")
    session.add(user)
    await session.flush()
    return user.id


def _workout(user_id: UUID, deleted_at: datetime | None) -> WorkoutSession:
    return WorkoutSession(user_id=user_id, deleted_at=deleted_at)


def _program(user_id: UUID, name: str, deleted_at: datetime | None) -> Program:
    return Program(
        owner_id=user_id,
        name=name,
        goal=ProgramGoal.hypertrophy,
        microcycle_length=4,
        mesocycle_length_microcycles=4,
        source=ProgramSource.manual,
        deleted_at=deleted_at,
    )


def _meal(user_id: UUID, deleted_at: datetime | None) -> Meal:
    return Meal(
        user_id=user_id,
        eaten_at=datetime.now(tz=UTC),
        meal_type=MealType.lunch,
        deleted_at=deleted_at,
    )


async def test_purge_removes_stale_rows_and_spares_recent() -> None:
    now = datetime.now(tz=UTC)
    old = now - timedelta(days=RETENTION_DAYS + 5)
    recent = now - timedelta(days=RETENTION_DAYS - 5)

    sm = get_sessionmaker()
    async with sm() as session:
        user_id = await _make_user(session)

        # One stale soft-deleted, one recently soft-deleted, one live per table.
        session.add_all(
            [
                _workout(user_id, old),
                _workout(user_id, recent),
                _workout(user_id, None),
                _program(user_id, "stale-prog", old),
                _program(user_id, "recent-prog", recent),
                _program(user_id, "live-prog", None),
                _meal(user_id, old),
                _meal(user_id, recent),
                _meal(user_id, None),
            ]
        )
        await session.commit()

        before_workouts = _counter_value("workout_sessions")
        before_programs = _counter_value("programs")
        before_meals = _counter_value("meals")

        result = await purge_soft_deleted(session, now=now)
        await session.commit()

        # Exactly the one stale row per table is purged.
        assert result.purged_by_table == {
            "workout_sessions": 1,
            "programs": 1,
            "meals": 1,
        }
        assert result.total == 3

        # The recent soft-deleted row and the live row survive in each table.
        workouts = (
            await session.execute(select(func.count()).select_from(WorkoutSession))
        ).scalar()
        programs = (await session.execute(select(func.count()).select_from(Program))).scalar()
        meals = (await session.execute(select(func.count()).select_from(Meal))).scalar()
        assert workouts == 2
        assert programs == 2
        assert meals == 2

        # The stale ones are the ones gone: no remaining row has deleted_at < cutoff.
        cutoff = now - timedelta(days=RETENTION_DAYS)
        stale_workouts = (
            await session.execute(
                select(func.count())
                .select_from(WorkoutSession)
                .where(WorkoutSession.deleted_at.is_not(None), WorkoutSession.deleted_at < cutoff)
            )
        ).scalar()
        assert stale_workouts == 0

        # Prometheus counter advanced by exactly one per table.
        assert _counter_value("workout_sessions") == before_workouts + 1
        assert _counter_value("programs") == before_programs + 1
        assert _counter_value("meals") == before_meals + 1


async def test_purge_is_noop_without_stale_rows() -> None:
    now = datetime.now(tz=UTC)
    recent = now - timedelta(days=1)

    sm = get_sessionmaker()
    async with sm() as session:
        user_id = await _make_user(session)
        session.add_all(
            [
                _workout(user_id, recent),
                _workout(user_id, None),
                _meal(user_id, None),
            ]
        )
        await session.commit()

        result = await purge_soft_deleted(session, now=now)
        await session.commit()

        assert result.total == 0
        assert result.purged_by_table == {
            "workout_sessions": 0,
            "programs": 0,
            "meals": 0,
        }
        remaining = (
            await session.execute(select(func.count()).select_from(WorkoutSession))
        ).scalar()
        assert remaining == 2
