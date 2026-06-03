"""body_metrics circumference columns (neck/waist/hip)

Revision ID: 0017_body_metrics_circumference
Revises: 0017_idempotency_ttl_index
Create Date: 2026-06-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0017_body_metrics_circumference"
down_revision: str | None = "0017_idempotency_ttl_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("body_metrics", sa.Column("neck_cm", sa.Numeric(5, 2), nullable=True))
    op.add_column("body_metrics", sa.Column("waist_cm", sa.Numeric(5, 2), nullable=True))
    op.add_column("body_metrics", sa.Column("hip_cm", sa.Numeric(5, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("body_metrics", "hip_cm")
    op.drop_column("body_metrics", "waist_cm")
    op.drop_column("body_metrics", "neck_cm")
