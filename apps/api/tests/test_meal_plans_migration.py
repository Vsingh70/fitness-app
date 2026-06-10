"""0022 data migration: existing meal_plans rows become targets_only daily plans.

This runs an isolated alembic downgrade/upgrade round-trip against the shared
test database. The autouse session fixture has already migrated to head; we step
back to 0021 (which re-adds the ``days`` jsonb), seed an old-shape plan, then
upgrade to 0022 and assert the row was preserved as a simple targets-only daily
plan with its targets intact. The test restores ``head`` at the end so other
tests are unaffected.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import anyio
from alembic.config import Config
from sqlalchemy import text

from app.db import get_sessionmaker


def _alembic_config() -> Config:
    base = Path(__file__).resolve().parent.parent
    cfg = Config(str(base / "alembic.ini"))
    cfg.set_main_option("script_location", str(base / "alembic"))
    return cfg


async def _alembic(action: str, revision: str) -> None:
    """Run an alembic up/downgrade in a worker thread. The alembic env.py calls
    ``asyncio.run`` internally, which can't be invoked from the test's running
    event loop, so it must run off-loop.
    """
    from alembic import command

    cfg = _alembic_config()

    def _run() -> None:
        if action == "upgrade":
            command.upgrade(cfg, revision)
        else:
            command.downgrade(cfg, revision)

    await anyio.to_thread.run_sync(_run)


async def test_data_migration_preserves_existing_plan_as_targets_only_daily() -> None:
    sm = get_sessionmaker()

    try:
        # Step back to before the structured-plans migration.
        await _alembic("downgrade", "0021_food_servings_fatsecret")

        async with sm() as db:
            user_id = (
                await db.execute(
                    text(
                        """
                        INSERT INTO users
                            (id, apple_sub, email, unit_system, timezone,
                             created_at, updated_at)
                        VALUES (gen_random_uuid(), 'migrate-sub', 'm@example.com',
                                'metric', 'UTC', NOW(), NOW())
                        RETURNING id
                        """
                    )
                )
            ).scalar_one()
            await db.execute(
                text(
                    """
                    INSERT INTO meal_plans
                        (id, user_id, name, target_kcal, target_protein_g, target_carbs_g,
                         target_fat_g, days, is_active, activated_at, created_at, updated_at)
                    VALUES
                        (gen_random_uuid(), :user_id, 'Legacy Cut', 2100, 175, 160, 65,
                         '{"mon": {"meals": []}}'::jsonb, true, NOW(), NOW(), NOW())
                    """
                ),
                {"user_id": user_id},
            )
            await db.commit()

        # Apply the structured-plans migration.
        await _alembic("upgrade", "0022_structured_meal_plans")

        async with sm() as db:
            row = (
                (
                    await db.execute(
                        text(
                            """
                        SELECT name, plan_kind, content_mode, tracking_mode,
                               target_kcal, target_protein_g, target_carbs_g, target_fat_g,
                               is_active
                        FROM meal_plans
                        WHERE name = 'Legacy Cut'
                        """
                        )
                    )
                )
                .mappings()
                .one()
            )

        assert row["name"] == "Legacy Cut"
        assert row["plan_kind"] == "daily_repeating"
        assert row["content_mode"] == "targets_only"
        assert row["tracking_mode"] == "macros_and_calories"
        assert Decimal(row["target_kcal"]) == Decimal("2100.00")
        assert Decimal(row["target_protein_g"]) == Decimal("175.00")
        assert Decimal(row["target_carbs_g"]) == Decimal("160.00")
        assert Decimal(row["target_fat_g"]) == Decimal("65.00")
        assert row["is_active"] is True

        # The unstructured blob is gone.
        async with sm() as db:
            cols = (
                await db.execute(
                    text(
                        """
                        SELECT column_name FROM information_schema.columns
                        WHERE table_name = 'meal_plans' AND column_name = 'days'
                        """
                    )
                )
            ).first()
        assert cols is None
    finally:
        # Make sure the DB ends back at head no matter what.
        await _alembic("upgrade", "head")
        async with sm() as db:
            await db.execute(text("DELETE FROM meal_plans"))
            await db.execute(text("DELETE FROM users WHERE apple_sub = 'migrate-sub'"))
            await db.commit()
