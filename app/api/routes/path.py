from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, learner_user
from app.models import User
from app.services.progression import list_progress_for_user

router = APIRouter(tags=["path"])


@router.get("/path/current")
async def get_current_path(
    user: User = Depends(learner_user),
    session: AsyncSession = Depends(db_session),
) -> dict:
    return {"items": await list_progress_for_user(session, user)}
