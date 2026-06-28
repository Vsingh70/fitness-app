"""Nightly garbage collection for dead refresh tokens.

Refresh tokens are never deleted in the request path — rotation, replay, and
logout only stamp ``revoked_at``, and expiry is enforced by comparison rather
than deletion. So ``refresh_tokens`` grows monotonically. This nightly sweep
hard-deletes tokens that are safely dead: expired, or revoked longer ago than
the retention window (kept that long so replay detection and audit still work on
recently-revoked tokens). Driven by an ARQ cron in ``app.workers.main``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.logging_config import get_logger
from app.models.refresh_token import RefreshToken
from app.observability.metrics import REFRESH_TOKENS_PURGED_TOTAL


async def purge_expired_refresh_tokens(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    retention_days: int | None = None,
) -> int:
    """Hard-delete refresh tokens that are expired or revoked beyond retention.

    Deletes rows where ``expires_at < cutoff`` OR ``revoked_at < cutoff`` (with
    ``cutoff = now - retention_days``). A NULL ``revoked_at`` never matches the
    second clause, so live tokens are spared; recently-expired or recently-revoked
    tokens are kept until they age past the window. Increments
    ``refresh_tokens_purged_total``. The caller commits the session.
    """
    if now is None:
        now = datetime.now(tz=UTC)
    if retention_days is None:
        retention_days = get_settings().refresh_token_retention_days
    cutoff = now - timedelta(days=retention_days)

    result = await session.execute(
        delete(RefreshToken).where(
            or_(
                RefreshToken.expires_at < cutoff,
                RefreshToken.revoked_at < cutoff,
            )
        )
    )
    purged = int(result.rowcount or 0)  # type: ignore[attr-defined]
    if purged:
        REFRESH_TOKENS_PURGED_TOTAL.inc(purged)

    get_logger("refresh_token_gc").info(
        "refresh_token_gc_done",
        retention_days=retention_days,
        cutoff=cutoff.isoformat(),
        purged=purged,
    )
    return purged
