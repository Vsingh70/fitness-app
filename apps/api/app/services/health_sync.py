"""Sync body measurements from Google Health (Fitbit account) into body_metrics.

Phase 2 of the Fitbit -> Google Health migration. Reads weight (and body-fat,
when reported) from the connected account and upserts into ``body_metrics`` so
scale readings appear in the user's weight history.

Token storage + refresh reuse the ``fitbit_connections`` table (provider-agnostic)
and the same secret-box encryption, mirroring ``fitbit_sync``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import google_health
from app.models.body_metric import BodyMetric
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


async def sync_user(session: AsyncSession, user_id: UUID) -> HealthSyncResult:
    """Pull weight + body-fat for one user and upsert into body_metrics."""
    connection = (
        await session.execute(select(FitbitConnection).where(FitbitConnection.user_id == user_id))
    ).scalar_one_or_none()
    if connection is None:
        logger.info("health_sync_skipped_no_connection", extra={"user_id": str(user_id)})
        return HealthSyncResult(0, 0)

    access_token = await _refresh_if_expiring(session, connection)

    weight = await google_health.list_weight(access_token=access_token)
    body_fat = await google_health.list_body_fat(access_token=access_token)

    weight_written = await _upsert_measurements(session, user_id=user_id, measurements=weight)
    body_fat_written = await _upsert_measurements(session, user_id=user_id, measurements=body_fat)

    connection.last_synced_at = _now()
    await session.flush()

    logger.info(
        "health_sync_done",
        extra={
            "user_id": str(user_id),
            "weight_written": weight_written,
            "body_fat_written": body_fat_written,
        },
    )
    return HealthSyncResult(weight_written=weight_written, body_fat_written=body_fat_written)


async def probe_user(session: AsyncSession, user_id: UUID) -> list[google_health.ProbeResult]:
    """TEMPORARY (spike): sweep candidate daily-metric dataType IDs for one user
    to discover real IDs + payload shapes. Remove with the probe in Phase B."""
    connection = (
        await session.execute(select(FitbitConnection).where(FitbitConnection.user_id == user_id))
    ).scalar_one_or_none()
    if connection is None:
        return []
    access_token = await _refresh_if_expiring(session, connection)
    return await google_health.probe_data_types(access_token=access_token)
