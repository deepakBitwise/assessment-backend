from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import db_session, learner_user
from app.core.security import new_public_id
from app.models import Assessment, Attempt, AuditEvent, Submission, User
from app.schemas import AttemptCreateRequest, AttemptResponse
from app.services.progression import list_progress_for_user

router = APIRouter(tags=["attempts"])


@router.post("/attempts", response_model=AttemptResponse, status_code=status.HTTP_201_CREATED)
async def create_attempt(
    payload: AttemptCreateRequest,
    user: User = Depends(learner_user),
    session: AsyncSession = Depends(db_session),
) -> AttemptResponse:
    assessment = await session.scalar(
        select(Assessment)
        .where(Assessment.public_id == payload.assessment_id)
        .options(selectinload(Assessment.level))
    )
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    progress = await list_progress_for_user(session, user)
    current_level = next(item for item in progress if item["level_id"] == assessment.level.public_id)
    if current_level["state"] == "locked":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Complete the previous level first.")

    existing_open = await session.scalar(
        select(Attempt).where(Attempt.user_id == user.id, Attempt.assessment_id == assessment.id, Attempt.state.in_(["in_progress", "under_review"]))
    )
    if existing_open is not None:
        return AttemptResponse(
            attempt_id=existing_open.public_id,
            rubric_version=existing_open.rubric_version,
            state=existing_open.state,
            attempt_no=existing_open.attempt_no,
        )

    last_attempt_no = await session.scalar(
        select(func.max(Attempt.attempt_no)).where(Attempt.user_id == user.id, Attempt.assessment_id == assessment.id)
    )
    next_attempt_no = (last_attempt_no or 0) + 1
    max_attempts = assessment.spec.get("pass_criteria", {}).get("max_attempts", 3)
    if next_attempt_no > max_attempts:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Maximum attempts reached for this level.")

    latest_attempt = await session.scalar(
        select(Attempt)
        .where(Attempt.user_id == user.id, Attempt.assessment_id == assessment.id)
        .order_by(Attempt.attempt_no.desc())
    )
    if latest_attempt and latest_attempt.cooldown_until and latest_attempt.cooldown_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cooldown active until {latest_attempt.cooldown_until.isoformat()}",
        )

    attempt = Attempt(
        public_id=new_public_id("att"),
        user_id=user.id,
        assessment_id=assessment.id,
        attempt_no=next_attempt_no,
        state="in_progress",
        rubric_version=assessment.rubric_version,
    )
    session.add(attempt)
    session.add(AuditEvent(actor_public_id=user.public_id, entity_ref=attempt.public_id, kind="attempt.created", payload={"assessment_id": assessment.public_id}))
    await session.commit()
    return AttemptResponse(attempt_id=attempt.public_id, rubric_version=attempt.rubric_version, state=attempt.state, attempt_no=attempt.attempt_no)
