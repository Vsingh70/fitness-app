"""Nightly garbage collection for soft-deleted rows.

Workout sessions, programs, and meals use soft delete (a nullable
``deleted_at`` column) so users can restore them. After a retention window we
hard-delete those rows to reclaim storage and keep indexes lean.

The cleanup is driven by a nightly ARQ cron (see ``app.workers.main``). Each
purged row is counted into a Prometheus counter and a structlog summary is
emitted so the run is observable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.models.meal import Meal
from app.models.program import Program
from app.models.user import User
from app.models.workout import WorkoutSession
from app.observability.metrics import SOFT_DELETE_PURGED_TOTAL

# Rows soft-deleted longer ago than this are eligible for a hard delete.
RETENTION_DAYS = 90

# Account deletion uses a separate, shorter window: the Settings "Delete account"
# sheet promises a 7-day grace period before the account is permanently purged.
ACCOUNT_DELETION_GRACE_DAYS = 7

# Tables that use soft delete via ``deleted_at`` (model class + label name).
_SOFT_DELETE_MODELS = (
    WorkoutSession,
    Program,
    Meal,
)


@dataclass(frozen=True)
class PurgeResult:
    """How many rows were hard-deleted per table, keyed by table name."""

    purged_by_table: dict[str, int]

    @property
    def total(self) -> int:
        return sum(self.purged_by_table.values())


async def purge_soft_deleted(
    session: AsyncSession, *, now: datetime | None = None, retention_days: int = RETENTION_DAYS
) -> PurgeResult:
    """Hard-delete rows whose ``deleted_at`` is older than ``retention_days``.

    Spares rows that are not soft-deleted (``deleted_at IS NULL``) and rows
    deleted within the retention window. Increments the
    ``soft_delete_purged_total`` counter per table. The caller is responsible
    for committing the session.
    """
    if now is None:
        now = datetime.now(tz=UTC)
    cutoff = now - timedelta(days=retention_days)

    purged_by_table: dict[str, int] = {}
    for model in _SOFT_DELETE_MODELS:
        table_name = model.__tablename__
        result = await session.execute(
            delete(model).where(
                model.deleted_at.is_not(None),
                model.deleted_at < cutoff,
            )
        )
        purged = int(result.rowcount or 0)  # type: ignore[attr-defined]
        purged_by_table[table_name] = purged
        if purged:
            SOFT_DELETE_PURGED_TOTAL.labels(table=table_name).inc(purged)

    get_logger("soft_delete_gc").info(
        "soft_delete_gc_done",
        retention_days=retention_days,
        cutoff=cutoff.isoformat(),
        purged_by_table=purged_by_table,
        total_purged=sum(purged_by_table.values()),
    )
    return PurgeResult(purged_by_table=purged_by_table)


async def purge_deleted_users(
    session: AsyncSession,
    *,
    grace_days: int = ACCOUNT_DELETION_GRACE_DAYS,
    now: datetime | None = None,
) -> int:
    """Hard-delete users whose ``deleted_at`` is older than ``grace_days``.

    Account deletion (``DELETE /v1/me``) soft-deletes by stamping
    ``users.deleted_at``; this purge permanently removes the account once the
    grace window elapses. Every owned row (workout sessions, programs, meals,
    body metrics, refresh tokens, etc.) cascades away via the ``user_id``
    ``ON DELETE CASCADE`` FKs, so a single ``DELETE FROM users`` is sufficient.

    Spares users that are not deleted (``deleted_at IS NULL``) and those still
    within the grace window. Increments ``soft_delete_purged_total{table=users}``
    and returns the number of accounts purged. The caller commits the session.
    """
    if now is None:
        now = datetime.now(tz=UTC)
    cutoff = now - timedelta(days=grace_days)

    result = await session.execute(
        delete(User).where(
            User.deleted_at.is_not(None),
            User.deleted_at < cutoff,
        )
    )
    purged = int(result.rowcount or 0)  # type: ignore[attr-defined]
    if purged:
        SOFT_DELETE_PURGED_TOTAL.labels(table=User.__tablename__).inc(purged)

    get_logger("soft_delete_gc").info(
        "purge_deleted_users_done",
        grace_days=grace_days,
        cutoff=cutoff.isoformat(),
        purged=purged,
    )
    return purged
