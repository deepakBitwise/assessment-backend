from typing import Any
from fastapi import APIRouter, HTTPException
from sqlmodel import select
from sqlalchemy import func

from app.api.deps import SessionDep
from app.models import (
    HumanReview,
    HumanReviewCreate,
    HumanReviewPublic,
    HumanReviewUpdate,
    Submission,
    SubmissionStatus,
    get_datetime_utc,
)

router = APIRouter(prefix="/human-reviews", tags=["human-reviews"])

@router.post("/", response_model=HumanReviewPublic)
def create_human_review(
    review_in: HumanReviewCreate,
    session: SessionDep,
) -> Any:

    statement = select(func.count()).select_from(HumanReview)
    total_count = session.exec(statement).one()

    new_id = f"human-review-{total_count + 1}"

    review = HumanReview(
        id=new_id,
        submission_id=review_in.submission_id,
        assessment_id=review_in.assessment_id,
        weighted_score=review_in.weighted_score,
        provisional_verdict=review_in.provisional_verdict,
        review_payload=review_in.review_payload,
    )

    session.add(review)
    session.commit()
    session.refresh(review)

    return review


@router.get("/", response_model=list[HumanReviewPublic])
def get_reviews(session: SessionDep):

    statement = select(HumanReview)

    reviews = session.exec(statement).all()

    return reviews


@router.get("/{human_review_id}", response_model=HumanReviewPublic)
def get_review(
    human_review_id: str,
    session: SessionDep,
):
    review = session.get(HumanReview, human_review_id)

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    return review


@router.patch("/{human_review_id}")
def complete_review(
    human_review_id: str,
    review_update: HumanReviewUpdate,
    session: SessionDep,
):

    review = session.get(HumanReview, human_review_id)

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.reviewer_comments = review_update.reviewer_comments
    review.final_verdict = review_update.final_verdict
    review.updated_at = get_datetime_utc()

    session.add(review)

    submission = session.get(Submission, review.submission_id)

    if submission:
        submission.human_reviewer = (
            SubmissionStatus.PASSED
            if review_update.final_verdict == "PASSED"
            else SubmissionStatus.REJECTED
        )

        submission.updated_at = get_datetime_utc()

        session.add(submission)

    session.commit()

    return {
        "message": "Human review completed"
    }