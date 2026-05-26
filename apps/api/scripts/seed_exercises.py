"""Seed curated exercises from free-exercise-db into the database.

Idempotent: upserts by slug. Re-running is a no-op.

Usage:
    cd apps/api && uv run python -m scripts.seed_exercises
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import get_sessionmaker
from app.models.enums import (
    Equipment,
    MovementPattern,
    Muscle,
    TrackingType,
)
from app.models.exercise import Exercise

SEED_JSON = Path(__file__).resolve().parent.parent / "seed" / "exercises" / "exercises.json"

# Keep strength + cardio + their close cousins; drop oddities like stretching, plyometrics.
KEEP_CATEGORIES = {"strength", "powerlifting", "olympic weightlifting", "cardio"}

EQUIPMENT_MAP: dict[str, Equipment] = {
    "body only": Equipment.bodyweight,
    "dumbbell": Equipment.dumbbell,
    "barbell": Equipment.barbell,
    "cable": Equipment.cable,
    "machine": Equipment.machine,
    "kettlebells": Equipment.kettlebell,
    "bands": Equipment.banded,
    "e-z curl bar": Equipment.ez_bar,
}

# Source muscle -> our Muscle enum. Some source values map to multiple of ours;
# we pick a reasonable default and let movement_pattern + name carry the rest.
MUSCLE_MAP: dict[str, Muscle] = {
    "abdominals": Muscle.abs,
    "abductors": Muscle.abductors,
    "adductors": Muscle.adductors,
    "biceps": Muscle.biceps,
    "calves": Muscle.calves,
    "chest": Muscle.chest,
    "forearms": Muscle.forearms,
    "glutes": Muscle.glutes,
    "hamstrings": Muscle.hamstrings,
    "lats": Muscle.lats,
    "lower back": Muscle.lower_back,
    "middle back": Muscle.rhomboids,
    "quadriceps": Muscle.quads,
    "traps": Muscle.traps,
    "triceps": Muscle.triceps,
    # "shoulders" needs name-based disambiguation; handled in _classify_shoulder.
    # "neck" has no enum; we drop entries whose primary is neck.
}


def _classify_shoulder(name: str) -> Muscle:
    lower = name.lower()
    if any(
        token in lower
        for token in ("rear delt", "reverse fly", "rear-delt", "rear lateral", "face pull")
    ):
        return Muscle.rear_delts
    if any(token in lower for token in ("lateral raise", "side raise", "side lateral", "y raise")):
        return Muscle.side_delts
    return Muscle.front_delts


def map_muscle(source_muscle: str, name: str) -> Muscle | None:
    if source_muscle == "shoulders":
        return _classify_shoulder(name)
    if source_muscle == "neck":
        return None
    return MUSCLE_MAP.get(source_muscle)


SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    base = SLUG_RE.sub("-", name.lower()).strip("-")
    return base or "exercise"


# Heuristic movement_pattern rules, applied in order. Substring match on lowercased name.
MOVEMENT_RULES: list[tuple[str, MovementPattern]] = [
    ("rear delt", MovementPattern.horizontal_pull),
    ("reverse fly", MovementPattern.horizontal_pull),
    ("face pull", MovementPattern.horizontal_pull),
    ("pull-up", MovementPattern.vertical_pull),
    ("pull up", MovementPattern.vertical_pull),
    ("pullup", MovementPattern.vertical_pull),
    ("chin-up", MovementPattern.vertical_pull),
    ("chin up", MovementPattern.vertical_pull),
    ("chinup", MovementPattern.vertical_pull),
    ("pulldown", MovementPattern.vertical_pull),
    ("pull-down", MovementPattern.vertical_pull),
    ("row", MovementPattern.horizontal_pull),
    ("bench press", MovementPattern.horizontal_push),
    ("push-up", MovementPattern.horizontal_push),
    ("push up", MovementPattern.horizontal_push),
    ("pushup", MovementPattern.horizontal_push),
    ("dip", MovementPattern.horizontal_push),
    ("chest fly", MovementPattern.horizontal_push),
    ("chest press", MovementPattern.horizontal_push),
    ("overhead press", MovementPattern.vertical_push),
    ("military press", MovementPattern.vertical_push),
    ("shoulder press", MovementPattern.vertical_push),
    ("ohp", MovementPattern.vertical_push),
    ("squat", MovementPattern.squat),
    ("leg press", MovementPattern.squat),
    ("hack squat", MovementPattern.squat),
    ("deadlift", MovementPattern.hinge),
    ("rdl", MovementPattern.hinge),
    ("romanian", MovementPattern.hinge),
    ("good morning", MovementPattern.hinge),
    ("hip thrust", MovementPattern.hinge),
    ("kettlebell swing", MovementPattern.hinge),
    ("lunge", MovementPattern.lunge),
    ("split squat", MovementPattern.lunge),
    ("step up", MovementPattern.lunge),
    ("step-up", MovementPattern.lunge),
    ("carry", MovementPattern.carry),
    ("farmer", MovementPattern.carry),
    ("twist", MovementPattern.rotation),
    ("woodchopper", MovementPattern.rotation),
    ("russian twist", MovementPattern.rotation),
    ("pallof", MovementPattern.anti_rotation),
    ("plank", MovementPattern.anti_rotation),
    ("dead bug", MovementPattern.anti_rotation),
    ("hollow", MovementPattern.anti_rotation),
    ("clean", MovementPattern.hinge),
    ("snatch", MovementPattern.hinge),
    ("jerk", MovementPattern.vertical_push),
]


def infer_movement_pattern(name: str, category: str | None) -> MovementPattern:
    if category == "cardio":
        return MovementPattern.cardio
    lower = name.lower()
    for token, pattern in MOVEMENT_RULES:
        if token in lower:
            return pattern
    return MovementPattern.isolation


def infer_tracking_type(equipment: Equipment, movement_pattern: MovementPattern) -> TrackingType:
    if movement_pattern == MovementPattern.cardio:
        return (
            TrackingType.cardio_machine
            if equipment == Equipment.cardio_machine
            else TrackingType.distance_time
        )
    if equipment == Equipment.bodyweight:
        # Pull-ups, dips, push-ups: bodyweight reps; allow weighted variants later.
        if movement_pattern in (
            MovementPattern.vertical_pull,
            MovementPattern.horizontal_push,
        ):
            return TrackingType.weighted_bodyweight
        return TrackingType.bodyweight_reps
    return TrackingType.weight_reps


def _normalize_secondaries(
    source_secondaries: Iterable[str], name: str, primary: Muscle
) -> list[Muscle]:
    seen: set[Muscle] = {primary}
    out: list[Muscle] = []
    for raw in source_secondaries:
        mapped = map_muscle(raw, name)
        if mapped is None or mapped in seen:
            continue
        seen.add(mapped)
        out.append(mapped)
    return out


def _build_exercise_row(entry: dict[str, Any]) -> dict[str, Any] | None:
    category = entry.get("category")
    if category not in KEEP_CATEGORIES:
        return None

    src_equipment = entry.get("equipment")
    if src_equipment not in EQUIPMENT_MAP:
        return None

    primaries = entry.get("primaryMuscles") or []
    if not primaries:
        return None

    primary_muscle = map_muscle(primaries[0], entry["name"])
    if primary_muscle is None:
        return None

    equipment = EQUIPMENT_MAP[src_equipment]
    movement_pattern = infer_movement_pattern(entry["name"], category)
    tracking_type = infer_tracking_type(equipment, movement_pattern)
    secondaries = _normalize_secondaries(
        entry.get("secondaryMuscles") or [], entry["name"], primary_muscle
    )

    instructions = entry.get("instructions") or []
    notes = " ".join(instructions).strip() or None
    if notes and len(notes) > 4000:
        notes = notes[:3997] + "..."

    return {
        "name": entry["name"],
        "slug": slugify(entry["name"]),
        "owner_id": None,
        "primary_muscle": primary_muscle.value,
        "secondary_muscles": [m.value for m in secondaries],
        "equipment": equipment.value,
        "movement_pattern": movement_pattern.value,
        "tracking_type": tracking_type.value,
        "is_unilateral": False,
        "notes": notes,
        "cues": None,
    }


def load_seed_rows() -> list[dict[str, Any]]:
    raw = json.loads(SEED_JSON.read_text())
    rows: list[dict[str, Any]] = []
    seen_slugs: set[str] = set()
    for entry in raw:
        row = _build_exercise_row(entry)
        if row is None:
            continue
        slug = row["slug"]
        if slug in seen_slugs:
            # Dedup variants that collide on slug; keep the first occurrence.
            continue
        seen_slugs.add(slug)
        rows.append(row)
    return rows


async def seed() -> tuple[int, int]:
    """Upsert curated exercises. Returns (rows_processed, rows_inserted_or_updated)."""
    rows = load_seed_rows()
    if not rows:
        return 0, 0

    sm = get_sessionmaker()
    async with sm() as session:
        before = (
            (await session.execute(select(Exercise).where(Exercise.owner_id.is_(None))))
            .scalars()
            .all()
        )
        before_count = len(before)

        for row in rows:
            stmt = pg_insert(Exercise).values(**row)
            stmt = stmt.on_conflict_do_update(
                index_elements=["slug"],
                set_={
                    "name": stmt.excluded.name,
                    "primary_muscle": stmt.excluded.primary_muscle,
                    "secondary_muscles": stmt.excluded.secondary_muscles,
                    "equipment": stmt.excluded.equipment,
                    "movement_pattern": stmt.excluded.movement_pattern,
                    "tracking_type": stmt.excluded.tracking_type,
                    "is_unilateral": stmt.excluded.is_unilateral,
                    "notes": stmt.excluded.notes,
                    "cues": stmt.excluded.cues,
                },
                where=Exercise.owner_id.is_(None),
            )
            await session.execute(stmt)

        await session.commit()

        after = (
            (await session.execute(select(Exercise).where(Exercise.owner_id.is_(None))))
            .scalars()
            .all()
        )
        after_count = len(after)

    return len(rows), after_count - before_count


def main() -> int:
    processed, delta = asyncio.run(seed())
    print(f"Processed {processed} rows; inserted {delta} new curated exercises.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
