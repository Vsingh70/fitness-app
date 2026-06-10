"""Sync body measurements from Google Health (Fitbit account) into body_metrics.

Phase 2 of the Fitbit -> Google Health migration. Reads weight (and body-fat,
when reported) from the connected account and upserts into ``body_metrics`` so
scale readings appear in the user's weight history.

Token storage + refresh reuse the ``fitbit_connections`` table (provider-agnostic)
and the same secret-box encryption.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import google_health
from app.clients.google_health import DailySummary, GoogleHealthAuthError
from app.models.body_metric import BodyMetric
from app.models.daily_metric import DailyMetric
from app.models.fitbit_connection import FitbitConnection
from app.services.security import secretbox

logger = logging.getLogger(__name__)

REFRESH_LEEWAY = timedelta(minutes=5)


def _now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True)
class HealthSyncResult:
    weight_written: int
    body_fat_written: int
    daily_metrics_written: int = 0


async def _refresh_if_expiring(session: AsyncSession, connection: FitbitConnection) -> str:
    """Return a usable access token, refreshing in-place if near expiry."""
    if connection.expires_at - REFRESH_LEEWAY > _now():
        return secretbox.decrypt(connection.access_token_encrypted)

    refresh_token = secretbox.decrypt(connection.refresh_token_encrypted)
    fresh = await google_health.refresh_tokens(refresh_token=refresh_token)
    connection.access_token_encrypted = secretbox.encrypt(fresh.access_token)
    if fresh.refresh_token:
        connection.refresh_token_encrypted = secretbox.encrypt(fresh.refresh_token)
    connection.expires_at = fresh.expires_at
    if fresh.scopes:
        connection.scopes = fresh.scopes
    await session.flush()
    return fresh.access_token


async def _upsert_measurements(
    session: AsyncSession,
    *,
    user_id: UUID,
    measurements: list[google_health.HealthMeasurement],
) -> int:
    """Insert measurements that aren't already present.

    body_metrics has no unique constraint on (user_id, recorded_at), so we
    de-dupe against existing rows by exact recorded_at. When a row already exists
    at that timestamp we fill in any missing weight/body-fat field rather than
    inserting a duplicate.
    """
    if not measurements:
        return 0

    times = [m.recorded_at for m in measurements]
    existing_rows = (
        (
            await session.execute(
                select(BodyMetric).where(
                    BodyMetric.user_id == user_id, BodyMetric.recorded_at.in_(times)
                )
            )
        )
        .scalars()
        .all()
    )
    existing = {row.recorded_at: row for row in existing_rows}

    written = 0
    for m in measurements:
        row = existing.get(m.recorded_at)
        if row is None:
            row = BodyMetric(
                user_id=user_id,
                recorded_at=m.recorded_at,
                weight_kg=m.weight_kg,
                body_fat_pct=m.body_fat_pct,
            )
            session.add(row)
            existing[m.recorded_at] = row
            written += 1
        else:
            # Backfill a missing field on an existing reading (e.g. body-fat
            # arriving for a row that previously only had weight).
            changed = False
            if m.weight_kg is not None and row.weight_kg is None:
                row.weight_kg = m.weight_kg
                changed = True
            if m.body_fat_pct is not None and row.body_fat_pct is None:
                row.body_fat_pct = m.body_fat_pct
                changed = True
            if changed:
                written += 1
    await session.flush()
    return written


def _merge_daily(summaries_lists: list[list[DailySummary]]) -> dict[date, DailySummary]:
    """Merge the readers' partial DailySummary lists into one row per date.

    Each reader fills only its own field, so we combine non-null fields per date.
    A later list's non-null value wins for its field (readers don't overlap on
    fields in practice, but this stays well-defined if they ever do).
    """
    merged: dict[date, DailySummary] = {}
    for summaries in summaries_lists:
        for s in summaries:
            current = merged.get(s.date)
            if current is None:
                merged[s.date] = s
                continue
            merged[s.date] = DailySummary(
                date=s.date,
                steps=s.steps if s.steps is not None else current.steps,
                resting_hr=s.resting_hr if s.resting_hr is not None else current.resting_hr,
                hrv_ms=s.hrv_ms if s.hrv_ms is not None else current.hrv_ms,
                sleep_minutes=(
                    s.sleep_minutes if s.sleep_minutes is not None else current.sleep_minutes
                ),
            )
    return merged


async def _upsert_daily_metrics(
    session: AsyncSession,
    *,
    user_id: UUID,
    merged: dict[date, DailySummary],
) -> int:
    """Upsert merged daily summaries into daily_metrics.

    Only non-null fields are written, so syncing one metric never wipes another's
    prior value: both the insert VALUES and the on-conflict SET include only the
    columns this row actually has. updated_at is always set on conflict.
    """
    written = 0
    for s in merged.values():
        fields: dict[str, object] = {}
        if s.steps is not None:
            fields["steps"] = s.steps
        if s.resting_hr is not None:
            fields["resting_hr"] = s.resting_hr
        if s.hrv_ms is not None:
            fields["hrv_ms"] = s.hrv_ms
        if s.sleep_minutes is not None:
            fields["sleep_minutes"] = s.sleep_minutes
        if not fields:
            continue
        stmt = (
            pg_insert(DailyMetric)
            .values(user_id=user_id, date=s.date, **fields)
            .on_conflict_do_update(
                index_elements=["user_id", "date"],
                set_={**fields, "updated_at": _now()},
            )
        )
        await session.execute(stmt)
        written += 1
    return written


async def _safe_read(
    name: str,
    reader: Callable[..., Awaitable[list[DailySummary]]],
    *,
    access_token: str,
    since: datetime | None,
) -> list[DailySummary]:
    """Run one daily-metric reader, swallowing non-auth failures so one bad data
    type doesn't abort the whole sync. GoogleHealthAuthError propagates so the
    caller can mark the connection for reconnect.
    """
    try:
        return await reader(access_token=access_token, since=since)
    except GoogleHealthAuthError:
        raise
    except Exception as exc:  # noqa: BLE001 — isolate a single failing data type
        logger.warning(
            "health_sync_reader_failed",
            extra={"reader": name, "error": repr(exc)},
        )
        return []


async def sync_user(session: AsyncSession, user_id: UUID) -> HealthSyncResult:
    """Pull weight + body-fat into body_metrics and the daily metrics (steps,
    resting HR, HRV, sleep) into daily_metrics for one user."""
    connection = (
        await session.execute(select(FitbitConnection).where(FitbitConnection.user_id == user_id))
    ).scalar_one_or_none()
    if connection is None:
        logger.info("health_sync_skipped_no_connection", extra={"user_id": str(user_id)})
        return HealthSyncResult(0, 0, 0)

    # Capture the incremental lower bound from the EXISTING last_synced_at before
    # we overwrite it at the end of the sync. None last_synced_at => backfill window.
    since = google_health.compute_since(connection.last_synced_at)

    try:
        access_token = await _refresh_if_expiring(session, connection)

        weight = await google_health.list_weight(access_token=access_token, since=since)
        body_fat = await google_health.list_body_fat(access_token=access_token, since=since)

        weight_written = await _upsert_measurements(session, user_id=user_id, measurements=weight)
        body_fat_written = await _upsert_measurements(
            session, user_id=user_id, measurements=body_fat
        )

        summaries_lists = [
            await _safe_read(
                "steps", google_health.list_steps, access_token=access_token, since=since
            ),
            await _safe_read(
                "heart_rate", google_health.list_heart_rate, access_token=access_token, since=since
            ),
            await _safe_read("hrv", google_health.list_hrv, access_token=access_token, since=since),
            await _safe_read(
                "sleep", google_health.list_sleep, access_token=access_token, since=since
            ),
        ]
    except GoogleHealthAuthError:
        # The token is dead (e.g. 7-day Testing-mode refresh token expired).
        # Flag the connection so the client can prompt a reconnect, then re-raise
        # so the caller (cron/endpoint) records the failure.
        connection.needs_reauth = True
        await session.flush()
        raise

    merged = _merge_daily(summaries_lists)
    daily_metrics_written = await _upsert_daily_metrics(session, user_id=user_id, merged=merged)

    # Sync succeeded — clear any stale reconnect flag.
    connection.needs_reauth = False
    connection.last_synced_at = _now()
    await session.flush()

    logger.info(
        "health_sync_done",
        extra={
            "user_id": str(user_id),
            "weight_written": weight_written,
            "body_fat_written": body_fat_written,
            "daily_metrics_written": daily_metrics_written,
        },
    )
    return HealthSyncResult(
        weight_written=weight_written,
        body_fat_written=body_fat_written,
        daily_metrics_written=daily_metrics_written,
    )


async def probe_ecg_user(session: AsyncSession, user_id: UUID) -> list[google_health.ProbeResult]:
    """TEMPORARY (spike): sweep candidate ECG dataType IDs for one user to learn
    whether Google exposes ECG + its shape. Remove with the ECG probe."""
    connection = (
        await session.execute(select(FitbitConnection).where(FitbitConnection.user_id == user_id))
    ).scalar_one_or_none()
    if connection is None:
        return []
    access_token = await _refresh_if_expiring(session, connection)
    return await google_health.probe_ecg_data_types(access_token=access_token)
