"""DSL for authoring program templates.

Each template file lives in this directory, ends with `template = program(...)`,
and gets discovered by `scripts/seed_programs.py`. Example:

    from seed.programs._dsl import day, exercise, program

    SLUGS = {
        "bench": "barbell-bench-press-medium-grip",
        "squat": "barbell-squat",
        ...
    }

    template = program(
        slug="ppl-6day",
        name="Push Pull Legs",
        goal="hypertrophy",
        weeks=8,
        days_per_week=6,
        slug_map=SLUGS,
        days=[
            day("Push A", exercises=[
                exercise("bench", sets=4, reps=(6, 8), rpe=(7, 8), rest=180,
                         progression="double_progression"),
                ...
            ]),
            ...
        ],
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Progression = Literal["linear", "double_progression", "rpe_based", "none"]
Goal = Literal["hypertrophy", "strength", "powerbuilding", "fat_loss", "general", "custom"]


@dataclass
class Exercise:
    slug_key: str
    sets: int
    reps: tuple[int, int] | int | None = None
    rpe: tuple[float, float] | None = None
    rir: tuple[int, int] | None = None
    rest_seconds: int | None = None
    progression: Progression = "none"
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        reps_low, reps_high = _unpack_int_pair(self.reps)
        rpe_low, rpe_high = _unpack_float_pair(self.rpe)
        rir_low, rir_high = _unpack_int_pair(self.rir)
        out: dict[str, Any] = {
            "slug_key": self.slug_key,
            "sets": self.sets,
            "progression": self.progression,
        }
        if reps_low is not None:
            out["reps_low"] = reps_low
        if reps_high is not None:
            out["reps_high"] = reps_high
        if rpe_low is not None:
            out["rpe_low"] = rpe_low
        if rpe_high is not None:
            out["rpe_high"] = rpe_high
        if rir_low is not None:
            out["rir_low"] = rir_low
        if rir_high is not None:
            out["rir_high"] = rir_high
        if self.rest_seconds is not None:
            out["rest_seconds"] = self.rest_seconds
        if self.notes is not None:
            out["notes"] = self.notes
        return out


def _unpack_int_pair(value: tuple[int, int] | int | None) -> tuple[int | None, int | None]:
    if value is None:
        return None, None
    if isinstance(value, int):
        return value, value
    return value[0], value[1]


def _unpack_float_pair(value: tuple[float, float] | None) -> tuple[float | None, float | None]:
    if value is None:
        return None, None
    return value[0], value[1]


@dataclass
class Day:
    name: str
    exercises: list[Exercise] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "exercises": [ex.to_dict() for ex in self.exercises]}


@dataclass
class Program:
    slug: str
    name: str
    goal: Goal
    weeks: int
    days_per_week: int
    slug_map: dict[str, str]
    days: list[Day]
    description: str | None = None
    author: str | None = None

    def to_data(self) -> dict[str, Any]:
        return {
            "slug_map": dict(self.slug_map),
            "days": [d.to_dict() for d in self.days],
        }


def exercise(
    slug_key: str,
    *,
    sets: int,
    reps: tuple[int, int] | int | None = None,
    rpe: tuple[float, float] | None = None,
    rir: tuple[int, int] | None = None,
    rest: int | None = None,
    progression: Progression = "none",
    notes: str | None = None,
) -> Exercise:
    return Exercise(
        slug_key=slug_key,
        sets=sets,
        reps=reps,
        rpe=rpe,
        rir=rir,
        rest_seconds=rest,
        progression=progression,
        notes=notes,
    )


def day(name: str, *, exercises: list[Exercise]) -> Day:
    return Day(name=name, exercises=exercises)


def program(
    *,
    slug: str,
    name: str,
    goal: Goal,
    weeks: int,
    days_per_week: int,
    slug_map: dict[str, str],
    days: list[Day],
    description: str | None = None,
    author: str | None = None,
) -> Program:
    if len(days) != days_per_week:
        raise ValueError(
            f"days_per_week={days_per_week} but {len(days)} day(s) declared for {slug}"
        )
    referenced = {ex.slug_key for d in days for ex in d.exercises}
    missing = referenced - slug_map.keys()
    if missing:
        raise ValueError(f"Template {slug}: slug_map missing keys for {sorted(missing)}")
    return Program(
        slug=slug,
        name=name,
        goal=goal,
        weeks=weeks,
        days_per_week=days_per_week,
        slug_map=slug_map,
        days=days,
        description=description,
        author=author,
    )
