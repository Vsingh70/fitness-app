"""fitbit_connections.needs_reauth flag

Revision ID: 0018_fitbit_needs_reauth
Revises: 0017_body_metrics_circumference
Create Date: 2026-06-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0018_fitbit_needs_reauth"
down_revision: str | None = "0017_body_metrics_circumference"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "fitbit_connections",
        sa.Column(
            "needs_reauth",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("fitbit_connections", "needs_reauth")
