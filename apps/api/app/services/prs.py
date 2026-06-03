"""Personal-records timeline across all exercises.

Surfaces every set marked ``is_pr=true`` for the user, newest first, with the
e1RM delta versus the user's previous PR for that same exercise. Read-only:
the workouts service is what marks ``sets.is_pr`` during finish/PR detection;
this service only reads those rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.pagination import decode_cursor, encode_cursor

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


@dataclass(frozen=True)
class PREvent:
    set_id: UUID
    exercise_id: UUID
    exercise_name: str
    session_id: UUID
    achieved_at: datetime
    weight_kg: Decimal
    reps: int
    e1rm_kg: Decimal
    # e1RM improvement over the user's previous PR for this exercise. ``None``
    # for the first-ever PR on an exercise.
    e1rm_delta_kg: Decimal | None


async def list_pr_events(
    session: AsyncSession,
    user: User,
    *,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> tuple[list[PREvent], str | None]:
    """Return PR events newest-first with cursor pagination.

    Each event carries the e1RM delta versus the prior PR for the same
    exercise. The delta is computed with a window function over the *full*
    PR history so it stays correct across pagination boundaries.
    """
    limit = max(1, min(limit, MAX_LIMIT))

    params: dict[str, object] = {"user_id": user.id, "limit": limit + 1}

    cursor_filter = ""
    decoded = decode_cursor(cursor)
    if decoded is not None:
        try:
            cursor_at = datetime.fromisoformat(decoded["c"])
            cursor_id = UUID(decoded["i"])
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid cursor.") from exc
        cursor_filter = (
            "WHERE (ranked.achieved_at, ranked.set_id) < (:cursor_at, CAST(:cursor_id AS uuid))"
        )
        params["cursor_at"] = cursor_at
        params["cursor_id"] = cursor_id

    # The CTE computes each PR set's e1RM and, via LAG over the per-exercise
    # chronological order, the previous PR's e1RM so we can derive the delta.
    stmt = text(
        f"""
        WITH pr_sets AS (
            SELECT
                s.id AS set_id,
                ws.id AS session_id,
                ws.started_at AS achieved_at,
                e.id AS exercise_id,
                e.name AS exercise_name,
                s.weight_kg AS weight_kg,
                s.reps AS reps,
                ROUND(s.weight_kg * (1 + s.reps::numeric / 30), 2) AS e1rm_kg
            FROM sets s
            JOIN workout_exercises we ON we.id = s.workout_exercise_id
            JOIN workout_sessions ws ON ws.id = we.workout_session_id
            JOIN exercises e ON e.id = we.exercise_id
            WHERE ws.user_id = :user_id
              AND ws.deleted_at IS NULL
              AND ws.ended_at IS NOT NULL
              AND s.is_pr = TRUE
              AND s.weight_kg IS NOT NULL
              AND s.reps IS NOT NULL
        ),
        ranked AS (
            SELECT
                pr_sets.*,
                LAG(pr_sets.e1rm_kg) OVER (
                    PARTITION BY pr_sets.exercise_id
                    ORDER BY pr_sets.achieved_at, pr_sets.set_id
                ) AS prev_e1rm_kg
            FROM pr_sets
        )
        SELECT
            ranked.set_id,
            ranked.exercise_id,
            ranked.exercise_name,
            ranked.session_id,
            ranked.achieved_at,
            ranked.weight_kg,
            ranked.reps,
            ranked.e1rm_kg,
            ranked.prev_e1rm_kg
        FROM ranked
        {cursor_filter}
        ORDER BY ranked.achieved_at DESC, ranked.set_id DESC
        LIMIT :limit
        """
    )

    rows = (await session.execute(stmt, params)).all()

    next_cursor: str | None = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = encode_cursor({"c": last.achieved_at.isoformat(), "i": str(last.set_id)})

    events: list[PREvent] = []
    for r in rows:
        e1rm = Decimal(r.e1rm_kg)
        delta = None if r.prev_e1rm_kg is None else (e1rm - Decimal(r.prev_e1rm_kg))
        events.append(
            PREvent(
                set_id=r.set_id,
                exercise_id=r.exercise_id,
                exercise_name=r.exercise_name,
                session_id=r.session_id,
                achieved_at=r.achieved_at,
                weight_kg=Decimal(r.weight_kg),
                reps=r.reps,
                e1rm_kg=e1rm,
                e1rm_delta_kg=delta,
            )
        )
    return events, next_cursor
