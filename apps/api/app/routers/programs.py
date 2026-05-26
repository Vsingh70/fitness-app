from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.program import (
    ProgramResponse,
    ProgramTemplateFull,
    ProgramTemplateList,
    ProgramTemplateSummary,
)
from app.services import programs as svc

router = APIRouter(tags=["programs"])


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
