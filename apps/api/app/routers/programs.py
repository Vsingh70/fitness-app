from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.program import (
    DuplicateProgramResponse,
    ExerciseDeloadResponse,
    ProgramCreate,
    ProgramDayCreate,
    ProgramDayExerciseCreate,
    ProgramDayExerciseUpdate,
    ProgramDayResponse,
    ProgramDayUpdate,
    ProgramList,
    ProgramListItem,
    ProgramPositionResponse,
    ProgramResponse,
    ProgramTemplateFull,
    ProgramTemplateList,
    ProgramTemplateSummary,
    ProgramUpdate,
    SaveAsTemplateRequest,
    SaveAsTemplateResponse,
    SlotReorderRequest,
)
from app.services import programs as svc

router = APIRouter(tags=["programs"])


class AdvanceRequest(BaseModel):
    as_skip: bool = False


# Templates -----------------------------------------------------------------


@router.get("/program-templates", response_model=ProgramTemplateList)
async def list_program_templates(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ProgramTemplateList:
    templates = await svc.list_templates(session, current_user)
    return ProgramTemplateList(
        items=[ProgramTemplateSummary.model_validate(t) for t in templates],
    )


@router.get("/program-templates/{slug}", response_model=ProgramTemplateFull)
async def get_program_template(
    slug: str,
    session: AsyncSession = Depends(db_session),
    _current_user: User = Depends(get_current_user),
) -> ProgramTemplateFull:
    template = await svc.get_template_by_slug(session, slug)
    return ProgramTemplateFull.model_validate(template)


@router.post(
    "/program-templates/{slug}/copy",
    response_model=ProgramResponse,
    status_code=status.HTTP_201_CREATED,
)
async def copy_program_template(
    slug: str,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ProgramResponse:
    template = await svc.get_template_by_slug(session, slug)
    program = await svc.copy_template_to_program(session, current_user, template)
    await session.commit()
    full = await svc.get_program_full(session, current_user, program.id)
    return ProgramResponse.model_validate(full)


# Programs ------------------------------------------------------------------


@router.get("/programs", response_model=ProgramList)
async def list_programs(
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = Query(default=None),
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ProgramList:
    rows, next_cursor = await svc.list_my_programs(
        session, current_user, limit=limit, cursor=cursor
    )
    return ProgramList(
        items=[ProgramListItem.model_validate(r) for r in rows],
        next_cursor=next_cursor,
    )


@router.post("/programs", response_model=ProgramResponse, status_code=status.HTTP_201_CREATED)
async def create_program(
    payload: ProgramCreate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ProgramResponse:
    record = await svc.create_empty_program(session, current_user, payload)
    await session.commit()
    full = await svc.get_program_full(session, current_user, record.id)
    return ProgramResponse.model_validate(full)


@router.get("/programs/{program_id}", response_model=ProgramResponse)
async def get_program(
    program_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ProgramResponse:
    record = await svc.get_program_full(session, current_user, program_id)
    return ProgramResponse.model_validate(record)


@router.patch("/programs/{program_id}", response_model=ProgramResponse)
async def patch_program(
    program_id: UUID,
    payload: ProgramUpdate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ProgramResponse:
    await svc.update_program(session, current_user, program_id, payload)
    await session.commit()
    full = await svc.get_program_full(session, current_user, program_id)
    return ProgramResponse.model_validate(full)


@router.delete("/programs/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_program(
    program_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    await svc.delete_program(session, current_user, program_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Program slots -------------------------------------------------------------


@router.post(
    "/programs/{program_id}/slots",
    response_model=ProgramDayResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_program_slot(
    program_id: UUID,
    payload: ProgramDayCreate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ProgramDayResponse:
    slot = await svc.add_slot(session, current_user, program_id, payload)
    await session.commit()
    await session.refresh(slot, attribute_names=["exercises"])
    return ProgramDayResponse.model_validate(slot)


@router.patch("/program-slots/{slot_id}", response_model=ProgramResponse)
async def patch_program_slot(
    slot_id: UUID,
    payload: ProgramDayUpdate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ProgramResponse:
    program = await svc.update_slot(session, current_user, slot_id, payload)
    await session.commit()
    full = await svc.get_program_full(session, current_user, program.id)
    return ProgramResponse.model_validate(full)


@router.delete("/program-slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_program_slot(
    slot_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    await svc.delete_slot(session, current_user, slot_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/programs/{program_id}/slots/reorder", response_model=ProgramResponse)
async def reorder_program_slots(
    program_id: UUID,
    payload: SlotReorderRequest,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ProgramResponse:
    await svc.reorder_slots(session, current_user, program_id, payload.slot_ids)
    await session.commit()
    full = await svc.get_program_full(session, current_user, program_id)
    return ProgramResponse.model_validate(full)


# Slot exercises ------------------------------------------------------------


@router.post(
    "/program-slots/{slot_id}/exercises",
    response_model=ProgramResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_program_slot_exercise(
    slot_id: UUID,
    payload: ProgramDayExerciseCreate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ProgramResponse:
    record = await svc.add_exercise_to_slot(session, current_user, slot_id, payload)
    await session.commit()
    # Return the full program so the client picks up the new row in context.
    from sqlalchemy import select

    from app.models.program import ProgramDay

    program_id = (
        await session.execute(
            select(ProgramDay.program_id).where(ProgramDay.id == record.program_day_id)
        )
    ).scalar_one()
    full = await svc.get_program_full(session, current_user, program_id)
    return ProgramResponse.model_validate(full)


@router.patch("/program-day-exercises/{pde_id}", response_model=ProgramResponse)
async def patch_program_day_exercise(
    pde_id: UUID,
    payload: ProgramDayExerciseUpdate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ProgramResponse:
    record = await svc.update_program_exercise(session, current_user, pde_id, payload)
    await session.commit()
    from sqlalchemy import select

    from app.models.program import ProgramDay

    program_id = (
        await session.execute(
            select(ProgramDay.program_id).where(ProgramDay.id == record.program_day_id)
        )
    ).scalar_one()
    full = await svc.get_program_full(session, current_user, program_id)
    return ProgramResponse.model_validate(full)


@router.delete("/program-day-exercises/{pde_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_program_day_exercise(
    pde_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    await svc.delete_program_exercise(session, current_user, pde_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Rotation position + advance -----------------------------------------------


@router.get("/programs/{program_id}/position", response_model=ProgramPositionResponse)
async def get_program_position(
    program_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ProgramPositionResponse:
    position = await svc.get_position(session, current_user, program_id)
    await session.commit()
    return position


@router.post("/programs/{program_id}/advance", response_model=ProgramPositionResponse)
async def advance_program_position(
    program_id: UUID,
    payload: AdvanceRequest | None = None,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ProgramPositionResponse:
    as_skip = payload.as_skip if payload is not None else False
    position = await svc.advance_position(session, current_user, program_id, as_skip=as_skip)
    await session.commit()
    return position


# Activate / deactivate -----------------------------------------------------


@router.post("/programs/{program_id}/activate", response_model=ProgramResponse)
async def activate_program(
    program_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ProgramResponse:
    program = await svc.activate_program(session, current_user, program_id)
    await session.commit()
    full = await svc.get_program_full(session, current_user, program.id)
    return ProgramResponse.model_validate(full)


@router.post("/programs/{program_id}/deactivate", response_model=ProgramResponse)
async def deactivate_program(
    program_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ProgramResponse:
    await svc.deactivate_program(session, current_user, program_id)
    await session.commit()
    full = await svc.get_program_full(session, current_user, program_id)
    return ProgramResponse.model_validate(full)


# Duplicate / save-as-template ----------------------------------------------


@router.post(
    "/programs/{program_id}/duplicate",
    response_model=DuplicateProgramResponse,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_program(
    program_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> DuplicateProgramResponse:
    copy = await svc.duplicate_program(session, current_user, program_id)
    await session.commit()
    full = await svc.get_program_full(session, current_user, copy.id)
    return DuplicateProgramResponse(program=ProgramResponse.model_validate(full))


@router.post(
    "/programs/{program_id}/save-as-template",
    response_model=SaveAsTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_program_as_template(
    program_id: UUID,
    payload: SaveAsTemplateRequest,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> SaveAsTemplateResponse:
    template = await svc.save_as_template(
        session,
        current_user,
        program_id,
        name=payload.name,
        visibility=payload.visibility,
    )
    await session.commit()
    return SaveAsTemplateResponse(template=ProgramTemplateSummary.model_validate(template))


# Per-lift reactive deload --------------------------------------------------


@router.post(
    "/programs/{program_id}/exercises/{exercise_id}/deload",
    response_model=ExerciseDeloadResponse,
)
async def apply_exercise_deload(
    program_id: UUID,
    exercise_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ExerciseDeloadResponse:
    """Apply a reactive per-lift deload for a single exercise.

    Drops the exercise's working weight by the deload intensity factor and resets
    its progression counters so it ramps back up. Scoped to this one lift; the
    rest of the program is untouched.
    """
    prior, new_weight = await svc.apply_exercise_deload(
        session, current_user, program_id, exercise_id
    )
    await session.commit()
    return ExerciseDeloadResponse(
        exercise_id=exercise_id,
        prior_weight_kg=prior,
        new_weight_kg=new_weight,
        applied=new_weight is not None,
    )
