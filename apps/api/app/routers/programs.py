from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.program import (
    ActivateRequest,
    ActivateResponse,
    ProgramCreate,
    ProgramDayCreate,
    ProgramDayExerciseCreate,
    ProgramDayExerciseUpdate,
    ProgramDayResponse,
    ProgramList,
    ProgramListItem,
    ProgramResponse,
    ProgramTemplateFull,
    ProgramTemplateList,
    ProgramTemplateSummary,
    ProgramUpdate,
)
from app.services import programs as svc

router = APIRouter(tags=["programs"])


# Templates -----------------------------------------------------------------


@router.get("/program-templates", response_model=ProgramTemplateList)
async def list_program_templates(
    session: AsyncSession = Depends(db_session),
    _current_user: User = Depends(get_current_user),
) -> ProgramTemplateList:
    templates = await svc.list_templates(session)
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
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ProgramList:
    rows = await svc.list_my_programs(session, current_user)
    return ProgramList(items=[ProgramListItem.model_validate(r) for r in rows])


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


# Program days --------------------------------------------------------------


@router.post(
    "/programs/{program_id}/days",
    response_model=ProgramDayResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_program_day(
    program_id: UUID,
    payload: ProgramDayCreate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ProgramDayResponse:
    day = await svc.add_day(session, current_user, program_id, payload)
    await session.commit()
    await session.refresh(day, attribute_names=["exercises"])
    return ProgramDayResponse.model_validate(day)


@router.delete("/program-days/{day_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_program_day(
    day_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    await svc.delete_day(session, current_user, day_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Program day exercises -----------------------------------------------------


@router.post(
    "/program-days/{day_id}/exercises",
    status_code=status.HTTP_201_CREATED,
)
async def add_program_day_exercise(
    day_id: UUID,
    payload: ProgramDayExerciseCreate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ProgramResponse:
    record = await svc.add_exercise_to_day(session, current_user, day_id, payload)
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


# Activate / deactivate -----------------------------------------------------


@router.post("/programs/{program_id}/activate", response_model=ActivateResponse)
async def activate_program(
    program_id: UUID,
    payload: ActivateRequest,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ActivateResponse:
    program, scheduled_count, skipped_count = await svc.activate_program(
        session,
        current_user,
        program_id,
        start_date=payload.start_date,
        weekday_offset=payload.weekday_offset,
        skip_existing=payload.skip_existing,
    )
    await session.commit()
    full = await svc.get_program_full(session, current_user, program.id)
    return ActivateResponse(
        program=ProgramResponse.model_validate(full),
        scheduled_count=scheduled_count,
        skipped_count=skipped_count,
    )


@router.post("/programs/{program_id}/deactivate", response_model=ProgramResponse)
async def deactivate_program(
    program_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
    skip_existing: bool = True,
) -> ProgramResponse:
    await svc.deactivate_program(session, current_user, program_id, skip_existing=skip_existing)
    await session.commit()
    full = await svc.get_program_full(session, current_user, program_id)
    return ProgramResponse.model_validate(full)
