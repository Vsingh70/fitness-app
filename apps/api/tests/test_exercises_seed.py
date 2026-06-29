from sqlalchemy import func, select

from app.db import get_sessionmaker
from app.models.exercise import Exercise
from scripts.seed_exercises import load_all_rows, load_curated_rows, load_seed_rows, seed


def test_load_all_rows_dedupes_curated_against_free_db() -> None:
    """Curated rows are added only when their slug is new; collisions are skipped
    (free-db wins), and the merged set never emits a duplicate slug."""
    rows = load_all_rows()
    slugs = [r["slug"] for r in rows]
    assert len(slugs) == len(set(slugs))

    free = {r["slug"] for r in load_seed_rows()}
    added = [r for r in load_curated_rows() if r["slug"] not in free]
    assert added, "curated.json should add at least some genuinely new exercises"
    assert len(rows) == len(free) + len(added)


async def test_seed_populates_curated_exercises() -> None:
    processed, inserted = await seed()
    assert processed > 200, "expected the seed to produce well over 200 entries"
    assert inserted == processed, "first seed run should insert every row"

    sm = get_sessionmaker()
    async with sm() as session:
        count = (
            await session.execute(
                select(func.count()).select_from(Exercise).where(Exercise.owner_id.is_(None))
            )
        ).scalar_one()
    assert count == processed


async def test_seed_is_idempotent() -> None:
    first_processed, first_inserted = await seed()
    second_processed, second_inserted = await seed()
    assert second_processed == first_processed
    assert second_inserted == 0
    assert first_inserted == first_processed


async def test_seed_includes_common_lifts() -> None:
    await seed()
    sm = get_sessionmaker()
    async with sm() as session:
        names = [
            n
            for (n,) in (
                await session.execute(select(Exercise.name).where(Exercise.owner_id.is_(None)))
            ).all()
        ]
    haystack = " | ".join(names).lower()
    for expected in ("bench press", "squat", "deadlift", "pull-up"):
        assert expected in haystack, f"seed missing {expected!r}"


async def test_seed_includes_curated_machines() -> None:
    """The curated supplement adds common gym movements the public set lacks."""
    await seed()
    sm = get_sessionmaker()
    async with sm() as session:
        names = [
            n
            for (n,) in (
                await session.execute(select(Exercise.name).where(Exercise.owner_id.is_(None)))
            ).all()
        ]
    haystack = " | ".join(names).lower()
    for expected in ("pec deck", "rope triceps pushdown", "leg extension", "seated cable row"):
        assert expected in haystack, f"curated seed missing {expected!r}"
