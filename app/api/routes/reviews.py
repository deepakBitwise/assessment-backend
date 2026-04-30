from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import db_session, reviewer_user
from app.models import Attempt, HumanReview, Submission, User
from app.schemas import ReviewDecisionRequest
from app.services.evaluation import apply_review_outcome

router = APIRouter(tags=["reviews"])


@router.get("/reviews/queue")
async def review_queue(
    user: User = Depends(reviewer_user),
    session: AsyncSession = Depends(db_session),
) -> dict:
    submissions = (
        await session.scalars(
            select(Submission)
            .where(Submission.status == "under_review")
            .options(selectinload(Submission.attempt).selectinload(Attempt.assessment), selectinload(Submission.verdict))
        )
    ).all()
    items = []
    for submission in submissions:
        summary = submission.evaluation_summary or {}
        items.append(
            {
                "submission_id": submission.public_id,
                "attempt_id": submission.attempt.public_id,
                "assessment_id": submission.attempt.assessment.public_id,
                "judge_weighted_score": summary.get("weighted_score"),
                "requires_review": summary.get("requires_review", False),
            }
        )
    items.sort(key=lambda item: (abs((item.get("judge_weighted_score") or 0) - 3.5), item["submission_id"]))
    return {"items": items}


@router.post("/reviews/{submission_id}")
async def submit_review(
    submission_id: str,
    payload: ReviewDecisionRequest,
    user: User = Depends(reviewer_user),
    session: AsyncSession = Depends(db_session),
) -> dict:
    submission = await session.scalar(
        select(Submission)
        .where(Submission.public_id == submission_id)
        .options(selectinload(Submission.attempt).selectinload(Attempt.assessment), selectinload(Submission.verdict))
    )
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")
    review = HumanReview(
        submission_id=submission.id,
        reviewer_id=user.id,
        scores=payload.scores,
        notes=payload.notes,
        decision=payload.decision,
    )
    session.add(review)
    await session.flush()
    verdict = await apply_review_outcome(session, submission, review)
    return {"submission_id": submission.public_id, "state": verdict.state, "weighted_score": verdict.weighted_score}
