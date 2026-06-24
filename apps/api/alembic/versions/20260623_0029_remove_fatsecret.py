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
    # Goal: no ``foods`` row keeps ``source = 'fatsecret'`` — the Python
    # ``FoodSource`` enum no longer has that member, so any such row would fail
    # to map in the ORM.
    #
    # Originally this DELETEd the rows on the assumption a live DB had none. That
    # is false: on a real DB, FatSecret-sourced foods can exist AND be referenced
    # by the user's meal history. ``meal_items.food_id`` and
    # ``meal_plan_items.food_id`` are FKs to ``foods.id`` with ON DELETE RESTRICT,
    # so deleting a referenced food raises a ForeignKeyViolationError and aborts
    # the whole migration. Re-label instead of delete: this removes the
    # ``fatsecret`` source while preserving the logged meals (the rows and their
    # FKs are untouched).
    #
    # ``source::text = 'fatsecret'`` avoids Postgres' UnsafeNewEnumValueUsage on a
    # fresh DB where migration 0021 adds the value in the same upgrade transaction.
    # ``'custom'`` is an original enum value (committed long before), so assigning
    # it is safe.
    op.execute("UPDATE foods SET source = 'custom' WHERE source::text = 'fatsecret'")


def downgrade() -> None:
    # Data-only purge of rows that should never have existed; nothing to restore.
    pass
