"""0029 re-labels referenced FatSecret foods instead of deleting them.

Regression for a production deploy incident: ``0029`` originally ran
``DELETE FROM foods WHERE source = 'fatsecret'`` on the assumption a live DB had
no such rows. Prod did — and they were referenced by real meal history. The FKs
``meal_items.food_id`` / ``meal_plan_items.food_id`` are ON DELETE RESTRICT, so
the DELETE raised a ForeignKeyViolationError and aborted the whole migration.

The migration now re-labels ``source -> 'custom'`` (the Python ``FoodSource`` enum
no longer has ``fatsecret``, so the row must be relabelled to map), which removes
the ``fatsecret`` source while preserving the logged meal. Restores head at the end.
"""

from __future__ import annotations

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


async def test_0029_relabels_referenced_fatsecret_food() -> None:
    sm = get_sessionmaker()
    try:
        await _alembic("downgrade", "0028_structured_work_logging")

        async with sm() as db:
            user_id = (
                await db.execute(
                    text(
                        """
                        INSERT INTO users (id, apple_sub, email, unit_system, timezone,
                                           created_at, updated_at)
                        VALUES (gen_random_uuid(), 'fs-fk-sub', 'fsfk@example.com',
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
                        INSERT INTO foods (id, source, name, payload, created_at, updated_at)
                        VALUES (gen_random_uuid(), 'fatsecret', 'FS Food', '{}'::jsonb,
                                NOW(), NOW())
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
                        VALUES (gen_random_uuid(), :u, NOW(), 'lunch', NOW(), NOW())
                        RETURNING id
                        """
                    ),
                    {"u": user_id},
                )
            ).scalar_one()
            # The RESTRICT FK that broke the original DELETE.
            await db.execute(
                text(
                    """
                    INSERT INTO meal_items (id, meal_id, food_id, grams, unit,
                                            created_at, updated_at)
                    VALUES (gen_random_uuid(), :m, :f, 150, 'g', NOW(), NOW())
                    """
                ),
                {"m": meal_id, "f": food_id},
            )
            await db.commit()

        # Previously raised ForeignKeyViolationError; must now succeed.
        await _alembic("upgrade", "0029_remove_fatsecret")

        async with sm() as db:
            source = (
                await db.execute(
                    text("SELECT source::text FROM foods WHERE id = :f"),
                    {"f": food_id},
                )
            ).scalar_one()
            still_referenced = (
                await db.execute(
                    text("SELECT food_id = :f FROM meal_items WHERE meal_id = :m"),
                    {"f": food_id, "m": meal_id},
                )
            ).scalar_one()

        assert source == "custom"  # relabelled, not deleted
        assert still_referenced is True  # meal history preserved
    finally:
        await _alembic("upgrade", "head")
