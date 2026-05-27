"""Weekly per-user per-muscle volume rollup.

The single rollup SQL:
1. Picks the anchor date for each session: COALESCE(scheduled_for, started_at::date).
2. Computes ISO year/week from the anchor.
3. Joins sets -> workout_exercises -> workout_sessions -> exercises, restricted
   to working sets in the requested week and to a single user.
4. Resolves a "tonnage bodyweight" per session: session.bodyweight_kg, falling
   back to the most recent prior session's bodyweight via a correlated lookup.
5. Emits one row per (primary muscle) at weight 1.0 and one row per secondary
   muscle via unnest at weight 0.5.
6. Aggregates working_sets, tonnage_kg, and average_rir per muscle.

The function deletes any existing rows for (user, iso_year, iso_week) and
re-inserts.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class IsoWeek:
    iso_year: int
    iso_week: int


def iso_week_for(anchor: date) -> IsoWeek:
    iso_year, iso_week, _ = anchor.isocalendar()
    return IsoWeek(iso_year=iso_year, iso_week=iso_week)


_ROLLUP_SQL = text(
    """
    WITH session_anchor AS (
        SELECT
            ws.id              AS workout_session_id,
            ws.user_id,
            ws.bodyweight_kg,
            COALESCE(sched.scheduled_for, ws.started_at::date) AS anchor_date
        FROM workout_sessions ws
        LEFT JOIN scheduled_workouts sched
          ON sched.id = ws.scheduled_workout_id
        WHERE ws.user_id = :user_id
          AND ws.deleted_at IS NULL
          AND ws.ended_at IS NOT NULL
    ),
    session_in_week AS (
        SELECT *
        FROM session_anchor
        WHERE EXTRACT(ISOYEAR FROM anchor_date) = :iso_year
          AND EXTRACT(WEEK    FROM anchor_date) = :iso_week
    ),
    session_bw AS (
        SELECT
            siw.workout_session_id,
            siw.user_id,
            siw.anchor_date,
            COALESCE(
                siw.bodyweight_kg,
                (
                    SELECT prior.bodyweight_kg
                    FROM workout_sessions prior
                    WHERE prior.user_id = siw.user_id
                      AND prior.deleted_at IS NULL
                      AND prior.bodyweight_kg IS NOT NULL
                      AND prior.started_at < (
                          SELECT started_at FROM workout_sessions
                          WHERE id = siw.workout_session_id
                      )
                    ORDER BY prior.started_at DESC
                    LIMIT 1
                )
            ) AS effective_bw_kg
        FROM session_in_week siw
    ),
    working_sets AS (
        SELECT
            s.workout_exercise_id,
            s.weight_kg,
            s.reps,
            s.rir,
            we.exercise_id,
            ex.primary_muscle,
            ex.secondary_muscles,
            ex.tracking_type,
            sb.effective_bw_kg
        FROM sets s
        JOIN workout_exercises we ON we.id = s.workout_exercise_id
        JOIN session_bw sb ON sb.workout_session_id = we.workout_session_id
        JOIN exercises ex ON ex.id = we.exercise_id
        WHERE s.set_type = 'working'
    ),
    set_contributions AS (
        -- Primary muscle: 1.0 weighting.
        SELECT
            ws.primary_muscle AS muscle,
            1.0::numeric      AS muscle_weight,
            ws.weight_kg,
            ws.reps,
            ws.rir,
            ws.tracking_type,
            ws.effective_bw_kg
        FROM working_sets ws
        UNION ALL
        -- Secondary muscles: 0.5 weighting per muscle via unnest.
        SELECT
            sec.muscle::muscle AS muscle,
            0.5::numeric       AS muscle_weight,
            ws.weight_kg,
            ws.reps,
            ws.rir,
            ws.tracking_type,
            ws.effective_bw_kg
        FROM working_sets ws,
             unnest(ws.secondary_muscles) AS sec(muscle)
    )
    SELECT
        muscle,
        SUM(muscle_weight) AS working_sets,
        SUM(
            muscle_weight * COALESCE(
                CASE
                    WHEN weight_kg IS NOT NULL AND reps IS NOT NULL
                        THEN weight_kg * reps
                    WHEN tracking_type IN ('bodyweight_reps', 'weighted_bodyweight')
                         AND effective_bw_kg IS NOT NULL AND reps IS NOT NULL
                        THEN (effective_bw_kg + COALESCE(weight_kg, 0)) * reps
                    ELSE 0
                END,
                0
            )
        ) AS tonnage_kg,
        CASE WHEN COUNT(rir) > 0
             THEN ROUND(AVG(rir)::numeric, 2)
             ELSE NULL END AS average_rir
    FROM set_contributions
    GROUP BY muscle
    """
)


async def rollup_user_week(
    session: AsyncSession, user_id: UUID, iso_year: int, iso_week: int
) -> int:
    """Delete-then-insert the rollup rows for (user, iso_year, iso_week).

    Returns the number of muscle rows written.
    """
    await session.execute(
        text(
            "DELETE FROM muscle_volume_weekly "
            "WHERE user_id = :user_id AND iso_year = :iso_year AND iso_week = :iso_week"
        ),
        {"user_id": user_id, "iso_year": iso_year, "iso_week": iso_week},
    )
    rows = (
        await session.execute(
            _ROLLUP_SQL,
            {"user_id": user_id, "iso_year": iso_year, "iso_week": iso_week},
        )
    ).all()

    inserted = 0
    for row in rows:
        muscle, working_sets, tonnage_kg, average_rir = row
        if working_sets is None or working_sets == 0:
            continue
        await session.execute(
            text(
                "INSERT INTO muscle_volume_weekly "
                "(id, user_id, iso_year, iso_week, muscle, working_sets, tonnage_kg, average_rir) "
                "VALUES (gen_random_uuid(), :user_id, :iso_year, :iso_week, "
                "        :muscle, :working_sets, :tonnage_kg, :average_rir)"
            ),
            {
                "user_id": user_id,
                "iso_year": iso_year,
                "iso_week": iso_week,
                "muscle": muscle,
                "working_sets": working_sets,
                "tonnage_kg": tonnage_kg or Decimal("0"),
                "average_rir": average_rir,
            },
        )
        inserted += 1
    await session.flush()
    return inserted


async def rollup_all_users_active_week(session: AsyncSession, ref_date: date) -> int:
    """Roll up the ISO week containing `ref_date` for every user with at least
    one ended session in that week. Returns the number of (user, week) rollups
    executed.
    """
    iso_year, iso_week, _ = ref_date.isocalendar()
    rows = (
        await session.execute(
            text(
                """
                SELECT DISTINCT ws.user_id
                FROM workout_sessions ws
                LEFT JOIN scheduled_workouts sched ON sched.id = ws.scheduled_workout_id
                WHERE ws.deleted_at IS NULL
                  AND ws.ended_at IS NOT NULL
                  AND EXTRACT(ISOYEAR FROM COALESCE(sched.scheduled_for, ws.started_at::date))
                      = :iso_year
                  AND EXTRACT(WEEK FROM COALESCE(sched.scheduled_for, ws.started_at::date))
                      = :iso_week
                """
            ),
            {"iso_year": iso_year, "iso_week": iso_week},
        )
    ).all()
    count = 0
    for (user_id,) in rows:
        await rollup_user_week(session, user_id, iso_year, iso_week)
        count += 1
    return count


def affected_weeks_for_session_dates(dates: Iterable[date]) -> set[IsoWeek]:
    """Collapse a set of session dates into the set of ISO weeks they touch."""
    out: set[IsoWeek] = set()
    for d in dates:
        out.add(iso_week_for(d))
    return out


def iso_week_bounds(iso_year: int, iso_week: int) -> tuple[date, date]:
    """Return (monday, sunday) of the given ISO year+week."""
    monday = date.fromisocalendar(iso_year, iso_week, 1)
    return monday, monday + timedelta(days=6)


# ---------------------------------------------------------------------------
# Read path
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WeeklyVolumeRow:
    iso_year: int
    iso_week: int
    working_sets: Decimal
    tonnage_kg: Decimal
    average_rir: Decimal | None


@dataclass(frozen=True)
class MuscleWeekRow:
    muscle: str
    working_sets: Decimal
    tonnage_kg: Decimal


@dataclass(frozen=True)
class WeekSummary:
    iso_year: int
    iso_week: int
    total_working_sets: Decimal
    total_tonnage_kg: Decimal
    per_muscle: list[MuscleWeekRow]


async def fetch_series(
    session: AsyncSession,
    *,
    user_id: UUID,
    from_year: int,
    from_week: int,
    to_year: int,
    to_week: int,
) -> dict[str, list[WeeklyVolumeRow]]:
    """Return per-muscle weekly series for the requested inclusive window.

    Key: muscle name; value: list of points ordered by (iso_year, iso_week) asc.
    """
    rows = (
        await session.execute(
            text(
                """
                SELECT muscle, iso_year, iso_week, working_sets, tonnage_kg, average_rir
                FROM muscle_volume_weekly
                WHERE user_id = :user_id
                  AND (iso_year, iso_week) >= (:from_year, :from_week)
                  AND (iso_year, iso_week) <= (:to_year, :to_week)
                ORDER BY muscle, iso_year, iso_week
                """
            ),
            {
                "user_id": user_id,
                "from_year": from_year,
                "from_week": from_week,
                "to_year": to_year,
                "to_week": to_week,
            },
        )
    ).all()
    by_muscle: dict[str, list[WeeklyVolumeRow]] = {}
    for muscle, iy, iw, ws, tn, rir in rows:
        by_muscle.setdefault(str(muscle), []).append(
            WeeklyVolumeRow(
                iso_year=int(iy),
                iso_week=int(iw),
                working_sets=ws,
                tonnage_kg=tn,
                average_rir=rir,
            )
        )
    return by_muscle


async def fetch_current_week_summary(
    session: AsyncSession, *, user_id: UUID, today: date
) -> WeekSummary:
    iso_year, iso_week, _ = today.isocalendar()
    rows = (
        await session.execute(
            text(
                """
                SELECT muscle, working_sets, tonnage_kg
                FROM muscle_volume_weekly
                WHERE user_id = :user_id
                  AND iso_year = :iso_year
                  AND iso_week = :iso_week
                ORDER BY muscle
                """
            ),
            {"user_id": user_id, "iso_year": iso_year, "iso_week": iso_week},
        )
    ).all()
    per_muscle: list[MuscleWeekRow] = []
    total_sets = Decimal("0")
    total_tonnage = Decimal("0")
    for muscle, ws, tn in rows:
        per_muscle.append(MuscleWeekRow(muscle=str(muscle), working_sets=ws, tonnage_kg=tn))
        total_sets += ws or Decimal("0")
        total_tonnage += tn or Decimal("0")
    return WeekSummary(
        iso_year=iso_year,
        iso_week=iso_week,
        total_working_sets=total_sets,
        total_tonnage_kg=total_tonnage,
        per_muscle=per_muscle,
    )
