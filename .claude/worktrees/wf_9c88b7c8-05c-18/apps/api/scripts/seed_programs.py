"""Seed curated program templates into the database.

Idempotent: upserts by slug. Re-running is a no-op.

Usage:
    cd apps/api && uv run python -m scripts.seed_programs
"""

from __future__ import annotations

import asyncio
import importlib
import pkgutil
import sys
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import get_sessionmaker
from app.models.exercise import Exercise
from app.models.program import ProgramTemplate
from seed.programs._dsl import Program as DSLProgram


def discover_templates() -> list[DSLProgram]:
    """Import every non-private module in seed.programs and collect its `template`."""
    import seed.programs as pkg  # noqa: WPS433

    out: list[DSLProgram] = []
    for info in pkgutil.iter_modules(pkg.__path__):
        if info.name.startswith("_"):
            continue
        module = importlib.import_module(f"seed.programs.{info.name}")
        tpl = getattr(module, "template", None)
        if tpl is None or not isinstance(tpl, DSLProgram):
            continue
        out.append(tpl)
    return sorted(out, key=lambda t: t.slug)


async def validate_slug_resolution(templates: list[DSLProgram]) -> None:
    """Fail fast if any template references an exercise slug not in the DB."""
    sm = get_sessionmaker()
    async with sm() as session:
        rows = (
            await session.execute(select(Exercise.slug).where(Exercise.owner_id.is_(None)))
        ).all()
        known: set[str] = {row[0] for row in rows}
    missing: dict[str, set[str]] = {}
    for tpl in templates:
        for slug in tpl.slug_map.values():
            if slug not in known:
                missing.setdefault(tpl.slug, set()).add(slug)
    if missing:
        lines = [f"  {slug}: missing {sorted(s)}" for slug, s in missing.items()]
        raise RuntimeError("Template slug resolution failed:\n" + "\n".join(lines))


async def seed() -> tuple[int, int]:
    """Returns (processed, inserted_or_updated)."""
    templates = discover_templates()
    if not templates:
        return 0, 0
    await validate_slug_resolution(templates)

    sm = get_sessionmaker()
    async with sm() as session:
        before = (await session.execute(select(ProgramTemplate.slug))).scalars().all()
        before_count = len(before)

        for tpl in templates:
            row: dict[str, Any] = {
                "slug": tpl.slug,
                "name": tpl.name,
                "description": tpl.description,
                "author": tpl.author,
                "goal": tpl.goal,
                "weeks": tpl.weeks,
                "days_per_week": tpl.days_per_week,
                "data": tpl.to_data(),
            }
            stmt = pg_insert(ProgramTemplate).values(**row)
            stmt = stmt.on_conflict_do_update(
                index_elements=["slug"],
                set_={
                    "name": stmt.excluded.name,
                    "description": stmt.excluded.description,
                    "author": stmt.excluded.author,
                    "goal": stmt.excluded.goal,
                    "weeks": stmt.excluded.weeks,
                    "days_per_week": stmt.excluded.days_per_week,
                    "data": stmt.excluded.data,
                },
            )
            await session.execute(stmt)
        await session.commit()

        after_count = (await session.execute(select(ProgramTemplate.slug))).scalars().all()

    return len(templates), len(after_count) - before_count


def main() -> int:
    processed, delta = asyncio.run(seed())
    print(f"Processed {processed} templates; inserted {delta} new.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
