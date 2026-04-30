from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import db_session, learner_user
from app.core.security import new_public_id
from app.models import Appeal, AuditEvent, Submission, User
from app.schemas import AppealCreateRequest

router = APIRouter(tags=["appeals"])


@router.post("/appeals", status_code=status.HTTP_201_CREATED)
async def create_appeal(
    payload: AppealCreateRequest,
    user: User = Depends(learner_user),
    session: AsyncSession = Depends(db_session),
) -> dict:
    submission = await session.scalar(
        select(Submission)
        .where(Submission.public_id == payload.submission_id)
        .options(selectinload(Submission.attempt), selectinload(Submission.verdict))
    )
    if submission is None or submission.attempt.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")
    if submission.verdict is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot appeal an unresolved submission.")

    appeal = Appeal(
        public_id=new_public_id("apl"),
        submission_id=submission.id,
        opened_by_id=user.id,
        reason=payload.reason,
        status="open",
    )
    session.add(appeal)
    session.add(AuditEvent(actor_public_id=user.public_id, entity_ref=submission.public_id, kind="appeal.opened", payload={"reason": payload.reason}))
    await session.commit()
    return {"appeal_id": appeal.public_id, "status": appeal.status}
