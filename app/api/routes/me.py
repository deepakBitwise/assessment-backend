from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, db_session
from app.models import User
from app.schemas import MeResponse, UserSummary
from app.services.progression import list_progress_for_user

router = APIRouter(tags=["me"])


@router.get("/me", response_model=MeResponse)
async def get_me(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> MeResponse:
    progress = await list_progress_for_user(session, user)
    cohort = None
    if user.cohort:
        cohort = {
            "slug": user.cohort.slug,
            "name": user.cohort.name,
            "rubric_version": user.cohort.rubric_version,
        }
    return MeResponse(user=UserSummary.model_validate(user), cohort=cohort, progress=progress)
