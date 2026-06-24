"""account deletion: users.deleted_at (soft-delete + 7-day grace)

Adds a nullable ``users.deleted_at`` timestamptz so account deletion is a soft
delete: ``DELETE /v1/me`` stamps ``deleted_at`` and revokes the user's refresh
tokens, the access token is then rejected on every authed request, and a nightly
purge hard-deletes users whose ``deleted_at`` is older than the 7-day grace
window (their owned rows cascade via the ``user_id`` ON DELETE CASCADE FKs).

Additive and online: a single nullable column, no backfill, no default. Existing
rows get ``NULL`` (not deleted), which is exactly the intended state.

Revision ID: 0030_user_deleted_at
Revises: 0029_remove_fatsecret
Create Date: 2026-06-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0030_user_deleted_at"
down_revision: str | None = "0029_remove_fatsecret"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "deleted_at")
