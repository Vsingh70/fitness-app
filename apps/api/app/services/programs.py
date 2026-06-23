from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    IntensityMode,
    ProgramGoal,
    ProgramSource,
    ProgressionStrategy,
    RepMode,
    TemplateVisibility,
)
from app.models.exercise import Exercise
from app.models.exercise_progression import ExerciseProgression
from app.models.program import Program, ProgramDay, ProgramDayExercise, ProgramTemplate
from app.models.program_progress import ProgramProgress
from app.models.user import User
from app.schemas.program import (
    ProgramCreate,
    ProgramDayCreate,
    ProgramDayExerciseCreate,
    ProgramDayExerciseUpdate,
    ProgramDayResponse,
    ProgramDayUpdate,
    ProgramPositionResponse,
    ProgramUpdate,
)
from app.services.pagination import decode_cursor, encode_cursor
from app.services.progression.mesocycle import DELOAD_INTENSITY_FACTOR
from app.services.rotation import RotationState, advance

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


def _now() -> datetime:
    return datetime.now(tz=UTC)


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


async def list_templates(session: AsyncSession, user: User) -> list[ProgramTemplate]:
    """Visible templates: curated (owner NULL) + the requester's own + every
    shared template. Curated come first, then by name.
    """
    stmt = (
        select(ProgramTemplate)
        .where(
            or_(
                ProgramTemplate.owner_id.is_(None),
                ProgramTemplate.owner_id == user.id,
                ProgramTemplate.visibility == TemplateVisibility.shared,
            )
        )
        .order_by(ProgramTemplate.owner_id.isnot(None), ProgramTemplate.name)
    )
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


def _derive_intensity_mode(slots_data: list[dict[str, Any]]) -> IntensityMode:
    """Pick the program's global intensity scale from the template content.

    The template DSL carries per-exercise rpe_*/rir_* values but no explicit
    program-level scale. Prefer RPE if any exercise specifies an rpe value, else
    RIR if any specifies an rir value, else Off (e.g. percentage/AMRAP plans).
    """
    has_rpe = False
    has_rir = False
    for slot_data in slots_data:
        for ex_data in slot_data.get("exercises", []):
            if ex_data.get("rpe_low") is not None or ex_data.get("rpe_high") is not None:
                has_rpe = True
            if ex_data.get("rir_low") is not None or ex_data.get("rir_high") is not None:
                has_rir = True
    if has_rpe:
        return IntensityMode.rpe
    if has_rir:
        return IntensityMode.rir
    return IntensityMode.off


def _derive_rep_mode(ex_data: dict[str, Any]) -> RepMode:
    """A span (reps_high present and != reps_low) is a range; otherwise a single
    rep goal (target)."""
    reps_low = ex_data.get("reps_low")
    reps_high = ex_data.get("reps_high")
    if reps_high is not None and reps_high != reps_low:
        return RepMode.range
    return RepMode.target


async def copy_template_to_program(
    session: AsyncSession, user: User, template: ProgramTemplate
) -> Program:
    """Atomic: build the full nested program in one transaction.

    ``template.data`` has shape::

        {
          "slug_map": { "bench": "barbell-bench-press---medium-grip", ... },
          "slots": [
              {"name": "Push A", "is_rest_day": False, "exercises": [
                  {"slug_key": "bench", "sets": 4, "reps_low": 6, "reps_high": 8,
                   "rpe_low": 7, "rpe_high": 8, "rest_seconds": 180,
                   "progression": "double_progression", "notes": null},
                  ...
              ]},
              {"name": "Rest", "is_rest_day": True, "exercises": []},
              ...
          ]
        }
    """
    data = template.data
    slug_map: dict[str, str] = data.get("slug_map", {})
    slots_data = data.get("slots", [])

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
        microcycle_length=len(slots_data),
        mesocycle_length_microcycles=template.mesocycle_length_microcycles,
        source=ProgramSource.template,
        template_id=template.id,
        intensity_mode=_derive_intensity_mode(slots_data),
    )
    session.add(program)
    await session.flush()

    for slot_index, slot_data in enumerate(slots_data):
        slot = ProgramDay(
            program_id=program.id,
            slot_index=slot_index,
            name=slot_data["name"],
            is_rest_day=bool(slot_data.get("is_rest_day", False)),
        )
        session.add(slot)
        await session.flush()

        for position, ex_data in enumerate(slot_data.get("exercises", [])):
            slug_key = ex_data["slug_key"]
            real_slug = slug_map[slug_key]
            exercise = by_slug[real_slug]
            pde = ProgramDayExercise(
                program_day_id=slot.id,
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
                rep_mode=_derive_rep_mode(ex_data),
                progression_strategy=_resolve_progression(ex_data.get("progression")),
                notes=ex_data.get("notes"),
            )
            session.add(pde)

    await session.flush()
    return program


# ---------------------------------------------------------------------------
# Program reads
# ---------------------------------------------------------------------------


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


async def list_my_programs(
    session: AsyncSession,
    user: User,
    *,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> tuple[list[Program], str | None]:
    """Programs ordered (is_active desc, created_at desc, id desc) with keyset
    pagination over the same 3-key ordering."""
    limit = max(1, min(limit, MAX_LIMIT))
    stmt = (
        select(Program)
        .where(Program.owner_id == user.id, Program.deleted_at.is_(None))
        .order_by(Program.is_active.desc(), Program.created_at.desc(), Program.id.desc())
        .limit(limit + 1)
    )

    decoded = decode_cursor(cursor)
    if decoded is not None:
        try:
            cursor_active = bool(decoded["a"])
            cursor_created = datetime.fromisoformat(decoded["c"])
            cursor_id = UUID(decoded["i"])
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid cursor.") from exc
        created_id_after = or_(
            Program.created_at < cursor_created,
            and_(Program.created_at == cursor_created, Program.id < cursor_id),
        )
        if cursor_active:
            stmt = stmt.where(
                or_(
                    Program.is_active.is_(False),
                    and_(Program.is_active.is_(True), created_id_after),
                )
            )
        else:
            stmt = stmt.where(Program.is_active.is_(False), created_id_after)

    rows = list((await session.execute(stmt)).scalars().all())
    next_cursor: str | None = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = encode_cursor(
            {"a": last.is_active, "c": last.created_at.isoformat(), "i": str(last.id)}
        )
    return rows, next_cursor


async def create_empty_program(
    session: AsyncSession, user: User, payload: ProgramCreate
) -> Program:
    program = Program(
        owner_id=user.id,
        name=payload.name,
        description=payload.description,
        goal=payload.goal,
        microcycle_length=0,
        mesocycle_length_microcycles=4,
        source=ProgramSource.manual,
        periodization_mode=payload.periodization_mode,
        auto_deload_on_stall=payload.auto_deload_on_stall,
        intensity_mode=payload.intensity_mode,
    )
    session.add(program)
    await session.flush()
    return program


async def _owned_program(session: AsyncSession, user: User, program_id: UUID) -> Program:
    record = (
        await session.execute(
            select(Program).where(
                Program.id == program_id,
                Program.owner_id == user.id,
                Program.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Program not found.")
    return record


async def update_program(
    session: AsyncSession, user: User, program_id: UUID, payload: ProgramUpdate
) -> Program:
    record = await _owned_program(session, user, program_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(record, field, value)
    await session.flush()
    return record


async def delete_program(session: AsyncSession, user: User, program_id: UUID) -> None:
    record = await _owned_program(session, user, program_id)
    record.deleted_at = _now()
    record.is_active = False
    await session.flush()


# ---------------------------------------------------------------------------
# Slot CRUD (microcycle slots replace weekday-bound days)
# ---------------------------------------------------------------------------


async def _recompute_microcycle_length(session: AsyncSession, program: Program) -> None:
    """Recompute ``program.microcycle_length`` from the current slot count.

    Always server-derived; never trust a client value.
    """
    count = (
        await session.execute(
            select(func.count()).select_from(ProgramDay).where(ProgramDay.program_id == program.id)
        )
    ).scalar_one()
    program.microcycle_length = int(count)
    await session.flush()


async def add_slot(
    session: AsyncSession, user: User, program_id: UUID, payload: ProgramDayCreate
) -> ProgramDay:
    program = await _owned_program(session, user, program_id)
    next_index = (
        await session.execute(
            select(func.coalesce(func.max(ProgramDay.slot_index) + 1, 0)).where(
                ProgramDay.program_id == program.id
            )
        )
    ).scalar_one()
    name = payload.name
    if payload.is_rest_day and not name:
        name = "Rest"
    slot = ProgramDay(
        program_id=program.id,
        slot_index=int(next_index),
        name=name,
        is_rest_day=payload.is_rest_day,
    )
    session.add(slot)
    await session.flush()
    await _recompute_microcycle_length(session, program)
    return slot


async def _owned_slot(session: AsyncSession, user: User, slot_id: UUID) -> ProgramDay:
    record = (
        await session.execute(
            select(ProgramDay)
            .join(Program, Program.id == ProgramDay.program_id)
            .where(
                ProgramDay.id == slot_id,
                Program.owner_id == user.id,
                Program.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Program slot not found.")
    return record


async def delete_slot(session: AsyncSession, user: User, slot_id: UUID) -> UUID:
    record = await _owned_slot(session, user, slot_id)
    program_id = record.program_id
    deleted_index = record.slot_index
    await session.delete(record)
    await session.flush()
    await session.execute(
        update(ProgramDay)
        .where(
            ProgramDay.program_id == program_id,
            ProgramDay.slot_index > deleted_index,
        )
        .values(slot_index=ProgramDay.slot_index - 1)
    )
    await session.flush()
    program = await _owned_program(session, user, program_id)
    await _recompute_microcycle_length(session, program)
    return program_id


async def reorder_slots(
    session: AsyncSession, user: User, program_id: UUID, slot_ids: list[UUID]
) -> Program:
    """Assign ``slot_index`` by the order of ``slot_ids``.

    The provided ids must be exactly the program's current slot id set (no more,
    no fewer, no duplicates), else 422.
    """
    program = await _owned_program(session, user, program_id)
    existing = (
        (await session.execute(select(ProgramDay).where(ProgramDay.program_id == program.id)))
        .scalars()
        .all()
    )
    existing_ids = {s.id for s in existing}
    given_ids = set(slot_ids)
    if len(slot_ids) != len(given_ids) or given_ids != existing_ids:
        raise HTTPException(
            status_code=422,
            detail="slot_ids must be exactly the program's current slot ids.",
        )
    by_id = {s.id: s for s in existing}
    for index, slot_id in enumerate(slot_ids):
        by_id[slot_id].slot_index = index
    await session.flush()
    return program


async def toggle_rest(
    session: AsyncSession, user: User, slot_id: UUID, *, is_rest_day: bool
) -> Program:
    """Flip a slot's rest flag.

    Turning a training slot into a rest slot keeps its exercise rows intact
    (they reappear if toggled back); only the flag changes.
    """
    slot = await _owned_slot(session, user, slot_id)
    slot.is_rest_day = is_rest_day
    await session.flush()
    return await _owned_program(session, user, slot.program_id)


async def update_slot(
    session: AsyncSession, user: User, slot_id: UUID, payload: ProgramDayUpdate
) -> Program:
    slot = await _owned_slot(session, user, slot_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(slot, field, value)
    await session.flush()
    return await _owned_program(session, user, slot.program_id)


# ---------------------------------------------------------------------------
# Slot exercises
# ---------------------------------------------------------------------------


async def add_exercise_to_slot(
    session: AsyncSession,
    user: User,
    slot_id: UUID,
    payload: ProgramDayExerciseCreate,
) -> ProgramDayExercise:
    slot = await _owned_slot(session, user, slot_id)
    exercise = (
        await session.execute(select(Exercise).where(Exercise.id == payload.exercise_id))
    ).scalar_one_or_none()
    if exercise is None or (exercise.owner_id is not None and exercise.owner_id != user.id):
        raise HTTPException(status_code=404, detail="Exercise not found.")

    next_position = (
        await session.execute(
            select(func.coalesce(func.max(ProgramDayExercise.position) + 1, 0)).where(
                ProgramDayExercise.program_day_id == slot.id
            )
        )
    ).scalar_one()
    record = ProgramDayExercise(
        program_day_id=slot.id,
        exercise_id=exercise.id,
        position=int(next_position),
        target_sets=payload.target_sets,
        target_reps_low=payload.target_reps_low,
        target_reps_high=payload.target_reps_high,
        target_rpe_low=payload.target_rpe_low,
        target_rpe_high=payload.target_rpe_high,
        target_rir_low=payload.target_rir_low,
        target_rir_high=payload.target_rir_high,
        rest_seconds=payload.rest_seconds,
        rep_mode=payload.rep_mode,
        progression_strategy=payload.progression_strategy,
        notes=payload.notes,
    )
    session.add(record)
    await session.flush()
    return record


async def _owned_program_exercise(
    session: AsyncSession, user: User, pde_id: UUID
) -> ProgramDayExercise:
    record = (
        await session.execute(
            select(ProgramDayExercise)
            .join(ProgramDay, ProgramDay.id == ProgramDayExercise.program_day_id)
            .join(Program, Program.id == ProgramDay.program_id)
            .where(
                ProgramDayExercise.id == pde_id,
                Program.owner_id == user.id,
                Program.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Program exercise not found.")
    return record


async def update_program_exercise(
    session: AsyncSession,
    user: User,
    pde_id: UUID,
    payload: ProgramDayExerciseUpdate,
) -> ProgramDayExercise:
    record = await _owned_program_exercise(session, user, pde_id)
    updates = payload.model_dump(exclude_unset=True)
    # Validate the merged result: a partial patch must not leave reps_high set
    # without reps_low, or an inverted range.
    new_low = updates.get("target_reps_low", record.target_reps_low)
    new_high = updates.get("target_reps_high", record.target_reps_high)
    if new_high is not None and (new_low is None or new_high < new_low):
        raise HTTPException(
            status_code=422,
            detail="target_reps_high requires target_reps_low <= target_reps_high.",
        )
    for field, value in updates.items():
        setattr(record, field, value)
    await session.flush()
    return record


async def delete_program_exercise(session: AsyncSession, user: User, pde_id: UUID) -> None:
    record = await _owned_program_exercise(session, user, pde_id)
    day_id = record.program_day_id
    deleted_pos = record.position
    await session.delete(record)
    await session.flush()
    await session.execute(
        update(ProgramDayExercise)
        .where(
            ProgramDayExercise.program_day_id == day_id,
            ProgramDayExercise.position > deleted_pos,
        )
        .values(position=ProgramDayExercise.position - 1)
    )
    await session.flush()


# ---------------------------------------------------------------------------
# Activate / deactivate
# ---------------------------------------------------------------------------


async def _deactivate_user_active_programs(
    session: AsyncSession, user_id: UUID, *, except_program_id: UUID | None = None
) -> None:
    """Deactivate every currently-active program for this user."""
    active_rows = (
        (
            await session.execute(
                select(Program).where(
                    Program.owner_id == user_id,
                    Program.is_active.is_(True),
                    Program.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    for program in active_rows:
        if except_program_id is not None and program.id == except_program_id:
            continue
        program.is_active = False
    if active_rows:
        await session.flush()


async def activate_program(session: AsyncSession, user: User, program_id: UUID) -> Program:
    """Activate a program.

    Requires at least one training slot. Deactivates any other active program
    for the user. Re-activation resumes where it left off: a ``program_progress``
    row is only created if none exists.
    """
    program = await _owned_program(session, user, program_id)
    slots = (
        (
            await session.execute(
                select(ProgramDay)
                .where(ProgramDay.program_id == program.id)
                .order_by(ProgramDay.slot_index)
            )
        )
        .scalars()
        .all()
    )
    if not any(not slot.is_rest_day for slot in slots):
        raise HTTPException(status_code=422, detail="Program needs at least one training slot")

    await _deactivate_user_active_programs(session, user.id, except_program_id=program.id)

    program.is_active = True
    program.activated_at = _now()
    await session.flush()

    await get_or_create_progress(session, user.id, program)
    return program


async def deactivate_program(session: AsyncSession, user: User, program_id: UUID) -> Program:
    """Mark a program inactive. ``program_progress`` is left intact so a later
    re-activation resumes the rotation where it stopped."""
    program = await _owned_program(session, user, program_id)
    program.is_active = False
    await session.flush()
    return program


# ---------------------------------------------------------------------------
# Rotation position + advance
# ---------------------------------------------------------------------------


async def get_or_create_progress(
    session: AsyncSession, user_id: UUID, program: Program
) -> ProgramProgress:
    record = (
        await session.execute(
            select(ProgramProgress).where(
                ProgramProgress.user_id == user_id,
                ProgramProgress.program_id == program.id,
            )
        )
    ).scalar_one_or_none()
    if record is None:
        record = ProgramProgress(user_id=user_id, program_id=program.id)
        session.add(record)
        await session.flush()
    return record


def _slot_to_response(slot: ProgramDay) -> ProgramDayResponse:
    return ProgramDayResponse.model_validate(slot)


def _build_position_response(program: Program, prog: ProgramProgress) -> ProgramPositionResponse:
    slots = list(program.days)  # ordered by slot_index
    today: ProgramDay | None = None
    if slots:
        index = prog.current_slot_index % len(slots)
        today = slots[index]
    is_rest = bool(today and today.is_rest_day)

    next_training: ProgramDay | None = None
    if is_rest and slots:
        index = prog.current_slot_index % len(slots)
        ordered = slots[index + 1 :] + slots[: index + 1]
        next_training = next((s for s in ordered if not s.is_rest_day), None)

    return ProgramPositionResponse(
        current_slot_index=prog.current_slot_index,
        current_microcycle_number=prog.current_microcycle_number,
        current_repetition=prog.current_repetition,
        mesocycle_length_microcycles=program.mesocycle_length_microcycles,
        in_deload=prog.in_deload,
        today_slot=_slot_to_response(today) if today else None,
        is_rest_day=is_rest,
        next_training_slot=_slot_to_response(next_training) if next_training else None,
    )


async def get_position(
    session: AsyncSession, user: User, program_id: UUID
) -> ProgramPositionResponse:
    program = await get_program_full(session, user, program_id)
    prog = await get_or_create_progress(session, user.id, program)
    return _build_position_response(program, prog)


async def advance_position(
    session: AsyncSession,
    user: User,
    program_id: UUID,
    *,
    as_skip: bool = False,
) -> ProgramPositionResponse:
    program = await get_program_full(session, user, program_id)
    prog = await get_or_create_progress(session, user.id, program)

    state = RotationState(
        slot_index=prog.current_slot_index,
        repetition=prog.current_repetition,
        microcycle_number=prog.current_microcycle_number,
        in_deload=prog.in_deload,
    )
    new = advance(
        state,
        microcycle_length=program.microcycle_length,
        meso_length=program.mesocycle_length_microcycles,
        auto_deload=program.auto_deload,
    )
    prog.current_slot_index = new.slot_index
    prog.current_repetition = new.repetition
    prog.current_microcycle_number = new.microcycle_number
    prog.in_deload = new.in_deload
    if not as_skip:
        prog.last_completed_at = _now()
    await session.flush()
    return _build_position_response(program, prog)


# ---------------------------------------------------------------------------
# Duplicate + save-as-template
# ---------------------------------------------------------------------------


async def duplicate_program(session: AsyncSession, user: User, program_id: UUID) -> Program:
    """Deep-copy a program (slots + exercise rows) into an independent fork.

    The copy is ``source=copied``, ``template_id=None``, inactive, named
    ``"<name> (copy)"``, with no progress row.
    """
    source = await get_program_full(session, user, program_id)
    copy = Program(
        owner_id=user.id,
        name=await _disambiguate_name(session, user.id, f"{source.name} (copy)"),
        description=source.description,
        goal=source.goal,
        microcycle_length=source.microcycle_length,
        mesocycle_length_microcycles=source.mesocycle_length_microcycles,
        source=ProgramSource.copied,
        template_id=None,
        is_active=False,
        auto_deload=source.auto_deload,
        periodization_mode=source.periodization_mode,
        auto_deload_on_stall=source.auto_deload_on_stall,
        intensity_mode=source.intensity_mode,
    )
    session.add(copy)
    await session.flush()

    for slot in source.days:
        new_slot = ProgramDay(
            program_id=copy.id,
            slot_index=slot.slot_index,
            name=slot.name,
            is_rest_day=slot.is_rest_day,
        )
        session.add(new_slot)
        await session.flush()
        for pde in slot.exercises:
            session.add(
                ProgramDayExercise(
                    program_day_id=new_slot.id,
                    exercise_id=pde.exercise_id,
                    position=pde.position,
                    target_sets=pde.target_sets,
                    target_reps_low=pde.target_reps_low,
                    target_reps_high=pde.target_reps_high,
                    target_rpe_low=pde.target_rpe_low,
                    target_rpe_high=pde.target_rpe_high,
                    target_rir_low=pde.target_rir_low,
                    target_rir_high=pde.target_rir_high,
                    rest_seconds=pde.rest_seconds,
                    rep_mode=pde.rep_mode,
                    progression_strategy=pde.progression_strategy,
                    notes=pde.notes,
                )
            )
    await session.flush()
    return copy


async def _serialize_program_to_template_data(
    session: AsyncSession, program: Program
) -> dict[str, Any]:
    """Mirror ``copy_template_to_program`` in reverse: serialize a program's
    slots + exercises into the template ``data`` shape (slug_map + slots)."""
    exercise_ids = {pde.exercise_id for slot in program.days for pde in slot.exercises}
    slug_by_id: dict[UUID, str] = {}
    if exercise_ids:
        rows = (
            await session.execute(
                select(Exercise.id, Exercise.slug).where(Exercise.id.in_(exercise_ids))
            )
        ).all()
        slug_by_id = {row[0]: row[1] for row in rows}

    slug_map: dict[str, str] = {slug: slug for slug in slug_by_id.values()}

    slots: list[dict[str, Any]] = []
    for slot in program.days:
        ex_list: list[dict[str, Any]] = []
        for pde in slot.exercises:
            slug = slug_by_id.get(pde.exercise_id)
            if slug is None:
                continue
            ex_data: dict[str, Any] = {
                "slug_key": slug,
                "sets": pde.target_sets,
                "progression": pde.progression_strategy.value,
            }
            if pde.target_reps_low is not None:
                ex_data["reps_low"] = pde.target_reps_low
            if pde.target_reps_high is not None:
                ex_data["reps_high"] = pde.target_reps_high
            if pde.target_rpe_low is not None:
                ex_data["rpe_low"] = float(pde.target_rpe_low)
            if pde.target_rpe_high is not None:
                ex_data["rpe_high"] = float(pde.target_rpe_high)
            if pde.target_rir_low is not None:
                ex_data["rir_low"] = pde.target_rir_low
            if pde.target_rir_high is not None:
                ex_data["rir_high"] = pde.target_rir_high
            if pde.rest_seconds is not None:
                ex_data["rest_seconds"] = pde.rest_seconds
            if pde.notes is not None:
                ex_data["notes"] = pde.notes
            ex_list.append(ex_data)
        slots.append(
            {
                "name": slot.name,
                "is_rest_day": slot.is_rest_day,
                "exercises": ex_list,
            }
        )

    return {"slug_map": slug_map, "slots": slots}


async def save_as_template(
    session: AsyncSession,
    user: User,
    program_id: UUID,
    *,
    name: str,
    visibility: TemplateVisibility,
) -> ProgramTemplate:
    program = await get_program_full(session, user, program_id)
    data = await _serialize_program_to_template_data(session, program)
    slug = await _unique_template_slug(session, name)
    template = ProgramTemplate(
        slug=slug,
        name=name,
        description=program.description,
        author=None,
        goal=program.goal,
        microcycle_length=program.microcycle_length,
        mesocycle_length_microcycles=program.mesocycle_length_microcycles,
        owner_id=user.id,
        visibility=visibility,
        data=data,
    )
    session.add(template)
    await session.flush()
    return template


def _slugify(value: str) -> str:
    out = []
    for ch in value.lower().strip():
        if ch.isalnum():
            out.append(ch)
        elif ch in {" ", "-", "_"}:
            out.append("-")
    slug = "".join(out).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "template"


async def _unique_template_slug(session: AsyncSession, name: str) -> str:
    base = _slugify(name)
    existing = (
        (
            await session.execute(
                select(ProgramTemplate.slug).where(ProgramTemplate.slug.like(base + "%"))
            )
        )
        .scalars()
        .all()
    )
    existing_set = set(existing)
    if base not in existing_set:
        return base
    suffix = 2
    while True:
        candidate = f"{base}-{suffix}"
        if candidate not in existing_set:
            return candidate
        suffix += 1


# ---------------------------------------------------------------------------
# Per-lift reactive deload
# ---------------------------------------------------------------------------


async def apply_exercise_deload(
    session: AsyncSession, user: User, program_id: UUID, exercise_id: UUID
) -> tuple[Decimal | None, Decimal | None]:
    """Reduce a single exercise's working weight by the deload intensity factor
    and reset its progression counters so it ramps from scratch.

    Scoped to ONE exercise; never touches the rest of the program. Returns
    (prior_weight_kg, new_weight_kg).
    """
    program = await _owned_program(session, user, program_id)
    prog = (
        await session.execute(
            select(ExerciseProgression).where(
                ExerciseProgression.user_id == user.id,
                ExerciseProgression.exercise_id == exercise_id,
            )
        )
    ).scalar_one_or_none()
    if prog is None:
        # No progression state yet -> nothing to deload, but the request is
        # still scoped/valid. Create a zeroed row so counters are reset.
        prog = ExerciseProgression(user_id=user.id, exercise_id=exercise_id)
        session.add(prog)
        await session.flush()

    prior = prog.current_top_set_weight_kg
    new_weight: Decimal | None = None
    if prior is not None:
        raw = prior * DELOAD_INTENSITY_FACTOR
        new_weight = ((raw / Decimal("0.5")).quantize(Decimal("1")) * Decimal("0.5")).quantize(
            Decimal("0.01")
        )
        prog.current_top_set_weight_kg = new_weight

    prog.consecutive_failures = 0
    prog.consecutive_successes = 0
    prog.consecutive_above_range = 0
    prog.last_updated_at = _now()

    # Dismiss any active per-lift stagnation suggestion for this exercise so it
    # doesn't keep nagging once the user has acted on it.
    await _dismiss_exercise_deload_suggestion(session, user, program, exercise_id)
    await session.flush()
    return prior, new_weight


def _stagnation_subject(exercise_slug: str) -> str:
    return exercise_slug


async def _dismiss_exercise_deload_suggestion(
    session: AsyncSession, user: User, program: Program, exercise_id: UUID
) -> None:
    """Mark the active reactive-deload stagnation insight for this exercise as
    dismissed, if one exists. Looks the insight up by the exercise's slug, which
    is the stagnation ``subject``.
    """
    from app.models.analytics_insight import AnalyticsInsight
    from app.models.enums import AnalyticsInsightKind

    slug = (
        await session.execute(select(Exercise.slug).where(Exercise.id == exercise_id))
    ).scalar_one_or_none()
    if slug is None:
        return
    rows = (
        (
            await session.execute(
                select(AnalyticsInsight).where(
                    AnalyticsInsight.user_id == user.id,
                    AnalyticsInsight.kind == AnalyticsInsightKind.stagnation,
                    AnalyticsInsight.subject == _stagnation_subject(slug),
                    AnalyticsInsight.dismissed_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        row.dismissed_at = _now()


__all__ = [
    "ProgramGoal",
    "activate_program",
    "add_exercise_to_slot",
    "add_slot",
    "advance_position",
    "apply_exercise_deload",
    "copy_template_to_program",
    "create_empty_program",
    "deactivate_program",
    "delete_program",
    "delete_program_exercise",
    "delete_slot",
    "duplicate_program",
    "get_or_create_progress",
    "get_position",
    "get_program_full",
    "get_template_by_slug",
    "list_my_programs",
    "list_templates",
    "reorder_slots",
    "save_as_template",
    "toggle_rest",
    "update_program",
    "update_program_exercise",
    "update_slot",
]
