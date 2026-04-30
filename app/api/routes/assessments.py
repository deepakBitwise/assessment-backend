from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import db_session, learner_user
from app.models import Assessment, Level, User
from app.schemas import AssessmentBrief
from app.services.progression import list_progress_for_user

router = APIRouter(tags=["assessments"])


@router.get("/assessments/{level_ref}", response_model=AssessmentBrief)
async def get_assessment(
    level_ref: str,
    user: User = Depends(learner_user),
    session: AsyncSession = Depends(db_session),
) -> AssessmentBrief:
    query = (
        select(Assessment)
        .join(Level)
        .options(selectinload(Assessment.level))
        .where((Level.slug == level_ref) | (Level.public_id == level_ref))
    )
    if level_ref.isdigit():
        query = query.where(Level.ordinal == int(level_ref))
    assessment = await session.scalar(query.order_by(Assessment.active_from.desc()))
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    progress = await list_progress_for_user(session, user)
    level_state = next(item for item in progress if item["level_id"] == assessment.level.public_id)
    if level_state["state"] == "locked":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Level is still locked.")

    return AssessmentBrief(
        id=assessment.public_id,
        level=assessment.level.ordinal,
        slug=assessment.level.slug,
        title=assessment.title,
        capability=assessment.level.capability,
        course_anchor=assessment.level.course_anchor,
        version=assessment.version,
        rubric_version=assessment.rubric_version,
        summary=assessment.level.summary,
        spec=assessment.spec,
    )
