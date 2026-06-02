"""index on idempotency_keys.created_at for the daily TTL sweep

Revision ID: 0017_idempotency_ttl_index
Revises: 0016_fitbit_push
Create Date: 2026-06-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0017_idempotency_ttl_index"
down_revision: str | None = "0016_fitbit_push"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_idempotency_keys_created_at",
        "idempotency_keys",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_idempotency_keys_created_at", table_name="idempotency_keys")
