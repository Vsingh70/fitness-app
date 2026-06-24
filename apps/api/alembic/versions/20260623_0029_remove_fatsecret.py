"""remove FatSecret: purge any legacy fatsecret-sourced food rows

FatSecret was removed from the stack before it ever went live (no credentials,
no IP allowlist), in favor of self-hosting USDA FoodData Central + Open Food
Facts (see ``tasks/redesign/07-nutrition.md``). This migration retires the
dormant ``fatsecret`` data path.

- Deletes any ``foods`` rows with ``source = 'fatsecret'`` (and their cascaded
  ``food_servings``). On a live DB there are none — FatSecret never wrote a row —
  so this is a safety net that makes dropping the Python ``FoodSource.fatsecret``
  enum member safe (the ORM would otherwise fail to map an unknown DB value).
- The Postgres ``food_source`` enum keeps its ``fatsecret`` value: Postgres has no
  ``DROP VALUE``, and the spec explicitly calls for no enum change. The value is
  left dormant and unused (mirrors the 0021 enum-add downgrade note).

No schema/DDL change; data-only and idempotent.

Revision ID: 0029_remove_fatsecret
Revises: 0028_structured_work_logging
Create Date: 2026-06-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0029_remove_fatsecret"
down_revision: str | None = "0028_structured_work_logging"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # food_servings cascade-delete via the FK ON DELETE CASCADE.
    #
    # Compare via a text cast rather than the enum literal ``'fatsecret'``:
    # Postgres forbids *using* a newly-added enum value in the same transaction it
    # was added (``UnsafeNewEnumValueUsageError``), and on a fresh DB migration
    # 0021 (which adds the value) and this one can run in one upgrade transaction.
    # ``source::text = 'fatsecret'`` sidesteps that — text comparison needs no
    # committed enum-value catalog entry.
    op.execute("DELETE FROM foods WHERE source::text = 'fatsecret'")


def downgrade() -> None:
    # Data-only purge of rows that should never have existed; nothing to restore.
    pass
