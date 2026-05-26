from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ProgramGoal, ProgramSource, ProgressionStrategy
from app.models.exercise import Exercise
from app.models.program import Program, ProgramDay, ProgramDayExercise, ProgramTemplate
from app.models.user import User


async def list_templates(session: AsyncSession) -> list[ProgramTemplate]:
    stmt = select(ProgramTemplate).order_by(ProgramTemplate.name)
    return list((await session.execute(stmt)).scalars().all())


async def get_template_by_slug(session: AsyncSession, slug: str) -> ProgramTemplate:
    record = (
        await session.execute(select(ProgramTemplate).where(ProgramTemplate.slug == slug))
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Program template not found.")
    return record


async def _disambiguate_name(session: AsyncSession, owner_id: UUID, base_name: str) -> str:
    """Append (2), (3), ... if the user already owns programs with this name."""
    existing = (
        (
            await session.execute(
                select(Program.name).where(
                    Program.owner_id == owner_id,
                    func.lower(Program.name).like(func.lower(base_name) + "%"),
                    Program.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    if base_name not in existing:
        return base_name
    suffix = 2
    while True:
        candidate = f"{base_name} ({suffix})"
        if candidate not in existing:
            return candidate
        suffix += 1


def _resolve_progression(value: Any) -> ProgressionStrategy:
    if isinstance(value, ProgressionStrategy):
        return value
    if isinstance(value, str):
        try:
            return ProgressionStrategy(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=500, detail=f"Unknown progression_strategy {value!r}."
            ) from exc
    return ProgressionStrategy.none


async def copy_template_to_program(
    session: AsyncSession, user: User, template: ProgramTemplate
) -> Program:
    """Atomic: build the full nested program in one transaction.

    `template.data` has shape:
        {
          "slug_map": { "bench": "barbell-bench-press---medium-grip", ... },
          "days": [
              {"name": "Push A", "exercises": [
                  {"slug_key": "bench", "sets": 4, "reps_low": 6, "reps_high": 8,
                   "rpe_low": 7, "rpe_high": 8, "rest_seconds": 180,
                   "progression": "double_progression", "notes": null},
                  ...
              ]},
              ...
          ]
        }
    """
    data = template.data
    slug_map: dict[str, str] = data.get("slug_map", {})
    days_data = data.get("days", [])

    # Resolve every slug up front; fail before any insert if anything is missing.
    needed_slugs = list({slug for slug in slug_map.values()})
    if needed_slugs:
        rows = (
            (await session.execute(select(Exercise).where(Exercise.slug.in_(needed_slugs))))
            .scalars()
            .all()
        )
        by_slug = {row.slug: row for row in rows}
        missing = [slug for slug in needed_slugs if slug not in by_slug]
        if missing:
            raise HTTPException(
                status_code=409,
                detail=f"Template references missing exercise slugs: {sorted(missing)}",
            )
    else:
        by_slug = {}

    name = await _disambiguate_name(session, user.id, template.name)

    program = Program(
        owner_id=user.id,
        name=name,
        description=template.description,
        goal=template.goal,
        weeks=template.weeks,
        days_per_week=template.days_per_week,
        source=ProgramSource.template,
        template_id=template.id,
    )
    session.add(program)
    await session.flush()

    for day_index, day_data in enumerate(days_data):
        day = ProgramDay(
            program_id=program.id,
            day_index=day_index,
            name=day_data["name"],
        )
        session.add(day)
        await session.flush()

        for position, ex_data in enumerate(day_data.get("exercises", [])):
            slug_key = ex_data["slug_key"]
            real_slug = slug_map[slug_key]
            exercise = by_slug[real_slug]
            pde = ProgramDayExercise(
                program_day_id=day.id,
                exercise_id=exercise.id,
                position=position,
                target_sets=ex_data["sets"],
                target_reps_low=ex_data.get("reps_low"),
                target_reps_high=ex_data.get("reps_high"),
                target_rpe_low=ex_data.get("rpe_low"),
                target_rpe_high=ex_data.get("rpe_high"),
                target_rir_low=ex_data.get("rir_low"),
                target_rir_high=ex_data.get("rir_high"),
                rest_seconds=ex_data.get("rest_seconds"),
                progression_strategy=_resolve_progression(ex_data.get("progression")),
                notes=ex_data.get("notes"),
            )
            session.add(pde)

    await session.flush()
    return program


async def get_program_full(session: AsyncSession, user: User, program_id: UUID) -> Program:
    stmt = (
        select(Program)
        .where(
            Program.id == program_id,
            Program.owner_id == user.id,
            Program.deleted_at.is_(None),
        )
        .options(selectinload(Program.days).selectinload(ProgramDay.exercises))
    )
    record = (await session.execute(stmt)).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Program not found.")
    return record


__all__ = [
    "ProgramGoal",
    "copy_template_to_program",
    "get_program_full",
    "get_template_by_slug",
    "list_templates",
]
