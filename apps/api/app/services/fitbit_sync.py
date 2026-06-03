"""Fitbit sync orchestration.

`sync_user(session, user_id)`:
1. Loads the user's connection.
2. Refreshes the access token if expiring within REFRESH_LEEWAY.
3. Lists activities since `last_synced_activity_at` (or 14 days ago) and
   upserts on `(user_id, fitbit_log_id)`.
4. Pulls daily summaries for the last 14 days (where missing) and upserts on
   `(user_id, date)`.
5. Updates `last_synced_at` and (if any activities) `last_synced_activity_at`.

Idempotent: re-running with the same data produces no duplicates because of
the unique constraints on both tables.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import fitbit
from app.models.daily_metric import DailyMetric
from app.models.fitbit_activity import FitbitActivity
from app.models.fitbit_connection import FitbitConnection
from app.observability.metrics import FITBIT_SYNC_TOTAL
from app.observability.spans import traced_span
from app.services.security import secretbox

logger = logging.getLogger(__name__)

REFRESH_LEEWAY = timedelta(hours=1)
DAILY_LOOKBACK_DAYS = 14
ACTIVITY_INITIAL_LOOKBACK = timedelta(days=14)


@dataclass(frozen=True)
class SyncResult:
    activities_written: int
    daily_metrics_written: int


def _now() -> datetime:
    return datetime.now(tz=UTC)


async def _refresh_if_expiring(session: AsyncSession, connection: FitbitConnection) -> str:
    """Return a usable access token, refreshing the connection in-place if
    expiry is within REFRESH_LEEWAY of now.
    """
    if connection.expires_at - REFRESH_LEEWAY > _now():
        return secretbox.decrypt(connection.access_token_encrypted)

    refresh_token = secretbox.decrypt(connection.refresh_token_encrypted)
    fresh = await fitbit.refresh_tokens(refresh_token=refresh_token)
    connection.access_token_encrypted = secretbox.encrypt(fresh.access_token)
    connection.refresh_token_encrypted = secretbox.encrypt(fresh.refresh_token)
    connection.expires_at = fresh.expires_at
    if fresh.scopes:
        connection.scopes = fresh.scopes
    await session.flush()
    return fresh.access_token


async def _upsert_activities(
    session: AsyncSession,
    *,
    user_id: UUID,
    rows: list[fitbit.FitbitActivityRow],
) -> int:
    written = 0
    for row in rows:
        stmt = (
            pg_insert(FitbitActivity)
            .values(
                user_id=user_id,
                fitbit_log_id=row.fitbit_log_id,
                activity_type=row.activity_type,
                started_at=row.started_at,
                duration_seconds=row.duration_seconds,
                calories=row.calories,
                average_hr=row.average_hr,
                max_hr=row.max_hr,
                steps=row.steps,
                distance_meters=row.distance_meters,
                raw=row.raw,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "fitbit_log_id"],
                set_={
                    "activity_type": row.activity_type,
                    "started_at": row.started_at,
                    "duration_seconds": row.duration_seconds,
                    "calories": row.calories,
                    "average_hr": row.average_hr,
                    "max_hr": row.max_hr,
                    "steps": row.steps,
                    "distance_meters": row.distance_meters,
                    "raw": row.raw,
                    "updated_at": _now(),
                },
            )
        )
        await session.execute(stmt)
        written += 1
    return written


async def _upsert_daily(
    session: AsyncSession,
    *,
    user_id: UUID,
    summaries: list[fitbit.FitbitDailySummary],
) -> int:
    written = 0
    for s in summaries:
        stmt = (
            pg_insert(DailyMetric)
            .values(
                user_id=user_id,
                date=s.date,
                steps=s.steps,
                resting_hr=s.resting_hr,
                hrv_ms=s.hrv_ms,
                sleep_minutes=s.sleep_minutes,
                sleep_score=s.sleep_score,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "date"],
                set_={
                    "steps": s.steps,
                    "resting_hr": s.resting_hr,
                    "hrv_ms": s.hrv_ms,
                    "sleep_minutes": s.sleep_minutes,
                    "sleep_score": s.sleep_score,
                    "updated_at": _now(),
                },
            )
        )
        await session.execute(stmt)
        written += 1
    return written


def _activity_since(connection: FitbitConnection) -> datetime:
    if connection.last_synced_activity_at is not None:
        return connection.last_synced_activity_at
    return _now() - ACTIVITY_INITIAL_LOOKBACK


async def sync_user(session: AsyncSession, user_id: UUID) -> SyncResult:
    with traced_span("fitbit.sync.daily", user_id=user_id) as span:
        connection = (
            await session.execute(
                select(FitbitConnection).where(FitbitConnection.user_id == user_id)
            )
        ).scalar_one_or_none()
        if connection is None:
            if span.is_recording():
                span.set_attribute("fitbit.skipped", "no_connection")
            logger.info("fitbit_sync_skipped_no_connection", extra={"user_id": str(user_id)})
            return SyncResult(0, 0)

        try:
            access_token = await _refresh_if_expiring(session, connection)

            since = _activity_since(connection)
            activities = await fitbit.list_activities(
                access_token=access_token,
                after_date_iso=since.strftime("%Y-%m-%dT%H:%M:%S"),
            )
            activities_written = await _upsert_activities(
                session, user_id=user_id, rows=activities
            )

            today = _now().date()
            summaries: list[fitbit.FitbitDailySummary] = []
            for offset in range(DAILY_LOOKBACK_DAYS):
                day = today - timedelta(days=offset)
                summaries.append(await fitbit.daily_summary(access_token=access_token, day=day))
            daily_written = await _upsert_daily(session, user_id=user_id, summaries=summaries)

            connection.last_synced_at = _now()
            if activities:
                latest_started = max(a.started_at for a in activities)
                if (
                    connection.last_synced_activity_at is None
                    or latest_started > connection.last_synced_activity_at
                ):
                    connection.last_synced_activity_at = latest_started
            await session.flush()

            # Reactive readiness: recompute every day we just touched so HRV
            # backfills, late sleep edits, etc. update the score within one sync.
            from app.services import readiness as readiness_service

            for s in summaries:
                await readiness_service.recompute_for_user_date(
                    session, user_id, target_date=s.date
                )
        except Exception:
            FITBIT_SYNC_TOTAL.labels(outcome="error").inc()
            raise

        FITBIT_SYNC_TOTAL.labels(outcome="success").inc()
        if span.is_recording():
            span.set_attribute("fitbit.activities_written", activities_written)
            span.set_attribute("fitbit.daily_metrics_written", daily_written)

        return SyncResult(
            activities_written=activities_written,
            daily_metrics_written=daily_written,
        )


def latest_daily_metric_date(metrics: list[DailyMetric]) -> date | None:
    """Convenience for tests + read endpoints."""
    if not metrics:
        return None
    return max(m.date for m in metrics)
