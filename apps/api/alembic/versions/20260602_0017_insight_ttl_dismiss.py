"""Insight TTL / dismissal.

The `dismissed_at` column was already introduced for the heuristic engine in
0012_insights_v2, so this migration only needs to:

- Ensure `dismissed_at` exists (defensive: add if missing for older DBs).
- Add an index supporting the Today-screen query
  ``WHERE user_id = ? AND dismissed_at IS NULL ORDER BY created_at DESC``.

Revision ID: 0017_insight_ttl_dismiss
Revises: 0016_fitbit_push
Create Date: 2026-06-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0017_insight_ttl_dismiss"
down_revision: str | None = "0016_fitbit_push"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Defensive: the column shipped in 0012, but guard for any DB that predates
    # it so this migration is safe to run standalone.
    op.execute("ALTER TABLE analytics_insights ADD COLUMN IF NOT EXISTS dismissed_at timestamptz")

    # Index for the Today screen: active insights for a user, newest first.
    # Partial on (dismissed_at IS NULL) so it stays small and matches the
    # exact predicate the list/Today queries use.
    op.create_index(
        "ix_insights_user_active_created",
        "analytics_insights",
        ["user_id", sa.text("created_at DESC")],
        postgresql_where=sa.text("dismissed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_insights_user_active_created", table_name="analytics_insights")
    # Leave the dismissed_at column in place; it is owned by 0012_insights_v2.
