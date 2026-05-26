import re
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Equipment, MovementPattern, Muscle, TrackingType
from app.models.exercise import Exercise
from app.models.user import User
from app.schemas.exercise import ExerciseCreate, ExerciseUpdate
from app.services.pagination import (
    decode_created_at_id_cursor,
    encode_created_at_id_cursor,
)

DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 200

_slug_strip_re = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    base = _slug_strip_re.sub("-", name.lower()).strip("-")
    return base or "exercise"


def _now() -> datetime:
    return datetime.now(tz=UTC)


async def is_exercise_referenced(session: AsyncSession, exercise_id: UUID) -> bool:
    """True if any workout_exercise references this exercise."""
    from app.models.workout import WorkoutExercise

    found = (
        await session.execute(
            select(WorkoutExercise.id).where(WorkoutExercise.exercise_id == exercise_id).limit(1)
        )
    ).scalar_one_or_none()
    return found is not None


async def list_exercises(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    q: str | None = None,
    muscle: Muscle | None = None,
    equipment: Equipment | None = None,
    movement_pattern: MovementPattern | None = None,
    tracking_type: TrackingType | None = None,
    mine_only: bool = False,
    include_archived: bool = False,
    limit: int = DEFAULT_PAGE_LIMIT,
    cursor: str | None = None,
) -> tuple[list[Exercise], str | None]:
    limit = max(1, min(limit, MAX_PAGE_LIMIT))

    stmt = select(Exercise)

    if mine_only:
        if user_id is None:
            return [], None
        stmt = stmt.where(Exercise.owner_id == user_id)
    elif user_id is not None:
        stmt = stmt.where(or_(Exercise.owner_id.is_(None), Exercise.owner_id == user_id))
    else:
        stmt = stmt.where(Exercise.owner_id.is_(None))

    if not include_archived:
        stmt = stmt.where(Exercise.archived_at.is_(None))

    if q:
        # pg_trgm similarity for fuzzy search; falls back to ILIKE for short tokens.
        like_pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Exercise.name.ilike(like_pattern),
                func.similarity(Exercise.name, q) > 0.2,
            )
        )

    if muscle is not None:
        stmt = stmt.where(
            or_(
                Exercise.primary_muscle == muscle,
                Exercise.secondary_muscles.contains([muscle]),
            )
        )

    if equipment is not None:
        stmt = stmt.where(Exercise.equipment == equipment)
    if movement_pattern is not None:
        stmt = stmt.where(Exercise.movement_pattern == movement_pattern)
    if tracking_type is not None:
        stmt = stmt.where(Exercise.tracking_type == tracking_type)

    if q:
        stmt = stmt.order_by(
            desc(func.similarity(Exercise.name, q)),
            asc(Exercise.name),
            asc(Exercise.id),
        )
    else:
        # Stable cursor ordering: (created_at asc, id asc).
        stmt = stmt.order_by(asc(Exercise.created_at), asc(Exercise.id))
        decoded = decode_created_at_id_cursor(cursor)
        if decoded is not None:
            cursor_created, cursor_id = decoded
            stmt = stmt.where(
                or_(
                    Exercise.created_at > cursor_created,
                    and_(Exercise.created_at == cursor_created, Exercise.id > cursor_id),
                )
            )

    stmt = stmt.limit(limit + 1)
    rows = (await session.execute(stmt)).scalars().all()

    next_cursor: str | None = None
    if len(rows) > limit:
        rows = rows[:limit]
        if not q:  # cursor pagination disabled when ordering by similarity
            last = rows[-1]
            next_cursor = encode_created_at_id_cursor(last.created_at, last.id)

    return list(rows), next_cursor


async def get_exercise(session: AsyncSession, exercise_id: UUID, *, user: User | None) -> Exercise:
    exercise = (
        await session.execute(select(Exercise).where(Exercise.id == exercise_id))
    ).scalar_one_or_none()
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found.")
    if exercise.owner_id is not None and (user is None or exercise.owner_id != user.id):
        raise HTTPException(status_code=404, detail="Exercise not found.")
    return exercise


async def _allocate_slug(session: AsyncSession, name: str) -> str:
    base = slugify(name)
    candidate = base
    suffix = 2
    while True:
        existing = (
            await session.execute(select(Exercise.id).where(Exercise.slug == candidate))
        ).scalar_one_or_none()
        if existing is None:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1


async def create_exercise(session: AsyncSession, user: User, payload: ExerciseCreate) -> Exercise:
    slug = await _allocate_slug(session, payload.name)
    exercise = Exercise(
        name=payload.name,
        slug=slug,
        owner_id=user.id,
        primary_muscle=payload.primary_muscle,
        secondary_muscles=list(payload.secondary_muscles),
        equipment=payload.equipment,
        movement_pattern=payload.movement_pattern,
        tracking_type=payload.tracking_type,
        is_unilateral=payload.is_unilateral,
        notes=payload.notes,
        cues=payload.cues,
    )
    session.add(exercise)
    await session.flush()
    return exercise


def _ensure_owner(exercise: Exercise, user: User) -> None:
    if exercise.owner_id is None:
        raise HTTPException(status_code=403, detail="Curated exercises cannot be modified.")
    if exercise.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Exercise not found.")


async def update_exercise(
    session: AsyncSession,
    exercise: Exercise,
    user: User,
    payload: ExerciseUpdate,
) -> Exercise:
    _ensure_owner(exercise, user)
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] != exercise.name:
        exercise.slug = await _allocate_slug(session, updates["name"])
    for field, value in updates.items():
        setattr(exercise, field, value)
    await session.flush()
    return exercise


async def archive_exercise(session: AsyncSession, exercise: Exercise, user: User) -> Exercise:
    _ensure_owner(exercise, user)
    if exercise.archived_at is None:
        exercise.archived_at = _now()
        await session.flush()
    return exercise


async def delete_exercise(session: AsyncSession, exercise: Exercise, user: User) -> None:
    _ensure_owner(exercise, user)
    if await is_exercise_referenced(session, exercise.id):
        raise HTTPException(
            status_code=409,
            detail=(
                "This exercise is referenced by your workouts. Archive it instead of deleting."
            ),
        )
    await session.delete(exercise)
    await session.flush()
