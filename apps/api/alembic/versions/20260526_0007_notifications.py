"""notifications table

Revision ID: 0007_notifications
Revises: 0006_scheduling
Create Date: 2026-05-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_notifications"
down_revision: str | None = "0006_scheduling"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KINDS = ["workout_reminder"]


def upgrade() -> None:
    enum = postgresql.ENUM(*KINDS, name="notification_kind", create_type=True)
    enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "notifications",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "kind",
            postgresql.ENUM(name="notification_kind", create_type=False),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    sa.Enum(name="notification_kind").drop(op.get_bind(), checkfirst=True)
