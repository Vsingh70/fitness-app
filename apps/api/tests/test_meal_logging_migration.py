"""0023 meal-logging migration round-trip.

Steps back to 0022, seeds a pre-0023 meal + item (grams only), upgrades to 0023
and asserts the new columns exist and ``amount`` is back-filled from ``grams``.
Then exercises a full downgrade/upgrade round-trip to prove reversibility.
Restores ``head`` at the end so other tests are unaffected.
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
    from alembic import command

    cfg = _alembic_config()

    def _run() -> None:
        if action == "upgrade":
            command.upgrade(cfg, revision)
        else:
            command.downgrade(cfg, revision)

    await anyio.to_thread.run_sync(_run)


async def test_0023_backfills_amount_and_round_trips() -> None:
    sm = get_sessionmaker()
    try:
        await _alembic("downgrade", "0022_structured_meal_plans")

        async with sm() as db:
            user_id = (
                await db.execute(
                    text(
                        """
                        INSERT INTO users (id, apple_sub, email, unit_system, timezone,
                                           created_at, updated_at)
                        VALUES (gen_random_uuid(), 'log-migrate-sub', 'lm@example.com',
                                'metric', 'UTC', NOW(), NOW())
                        RETURNING id
                        """
                    )
                )
            ).scalar_one()
            food_id = (
                await db.execute(
                    text(
                        """
                        INSERT INTO foods (id, source, name, kcal_per_100g, payload,
                                           created_at, updated_at)
                        VALUES (gen_random_uuid(), 'usda', 'Legacy Food', 100,
                                '{}'::jsonb, NOW(), NOW())
                        RETURNING id
                        """
                    )
                )
            ).scalar_one()
            meal_id = (
                await db.execute(
                    text(
                        """
                        INSERT INTO meals (id, user_id, eaten_at, meal_type, created_at,
                                           updated_at)
                        VALUES (gen_random_uuid(), :user_id, NOW(), 'lunch', NOW(), NOW())
                        RETURNING id
                        """
                    ),
                    {"user_id": user_id},
                )
            ).scalar_one()
            await db.execute(
                text(
                    """
                    INSERT INTO meal_items (id, meal_id, food_id, grams, kcal,
                                            created_at, updated_at)
                    VALUES (gen_random_uuid(), :meal_id, :food_id, 150, 150,
                            NOW(), NOW())
                    """
                ),
                {"meal_id": meal_id, "food_id": food_id},
            )
            await db.commit()

        await _alembic("upgrade", "0023_meal_logging")

        async with sm() as db:
            row = (
                (
                    await db.execute(
                        text(
                            """
                            SELECT amount, unit, serving_id, grams
                            FROM meal_items WHERE meal_id = :meal_id
                            """
                        ),
                        {"meal_id": meal_id},
                    )
                )
                .mappings()
                .one()
            )
        assert Decimal(row["amount"]) == Decimal("150.000")
        assert row["unit"] == "g"
        assert row["serving_id"] is None
        assert Decimal(row["grams"]) == Decimal("150.00")

        # Full reversibility round-trip.
        await _alembic("downgrade", "0022_structured_meal_plans")
        async with sm() as db:
            cols = (
                await db.execute(
                    text(
                        """
                        SELECT column_name FROM information_schema.columns
                        WHERE table_name = 'meal_items'
                          AND column_name IN ('amount', 'unit', 'serving_id')
                        """
                    )
                )
            ).all()
        assert cols == []
        await _alembic("upgrade", "0023_meal_logging")
    finally:
        await _alembic("upgrade", "head")
        async with sm() as db:
            await db.execute(text("DELETE FROM meal_items"))
            await db.execute(text("DELETE FROM meals"))
            await db.execute(text("DELETE FROM foods WHERE name = 'Legacy Food'"))
            await db.execute(text("DELETE FROM users WHERE apple_sub = 'log-migrate-sub'"))
            await db.commit()
