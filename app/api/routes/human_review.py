from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import select
from sqlalchemy import func

from app.api.deps import SessionDep

from app.models import (
    HumanReview,
    HumanReviewCreate,
    HumanReviewUpdate,
    HumanReviewPublic,
    HumanReviewStatus,
    Submission,
    SubmissionStatus,
    get_datetime_utc,
)

router = APIRouter(
    prefix="/human-reviews",
    tags=["human-reviews"],
)


# CREATE HUMAN REVIEW
@router.post("/", response_model=HumanReviewPublic)
def create_human_review(
    review_in: HumanReviewCreate,
    session: SessionDep,
) -> Any:

    submission = session.get(
        Submission,
        review_in.submission_id,
    )

    if not submission:
        raise HTTPException(
            status_code=404,
            detail="Submission not found",
        )

    statement = select(func.count()).select_from(
        HumanReview
    )

    total_count = session.exec(statement).one()

    review_id = f"human-review-{total_count + 1}"

    review = HumanReview(
        id=review_id,
        submission_id=review_in.submission_id,
        evaluator_payload=review_in.evaluator_payload,
    )

    submission.human_reviewer = (
        SubmissionStatus.QUEUED
    )

    submission.updated_at = get_datetime_utc()

    session.add(review)
    session.add(submission)

    session.commit()
    session.refresh(review)

    return review


# LIST HUMAN REVIEWS
@router.get("/", response_model=list[HumanReviewPublic])
def list_human_reviews(
    session: SessionDep,
):

    statement = select(HumanReview).order_by(
        HumanReview.created_at.desc()
    )

    reviews = session.exec(statement).all()

    return reviews


# GET SINGLE REVIEW
@router.get(
    "/{human_review_id}",
    response_model=HumanReviewPublic,
)
def get_review(
    human_review_id: str,
    session: SessionDep,
):

    review = session.get(
        HumanReview,
        human_review_id,
    )

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Review not found",
        )

    return review


# UPDATE FINAL REVIEW
@router.patch(
    "/{human_review_id}",
    response_model=HumanReviewPublic,
)
def update_review(
    human_review_id: str,
    review_in: HumanReviewUpdate,
    session: SessionDep,
):

    review = session.get(
        HumanReview,
        human_review_id,
    )

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Review not found",
        )

    review.reviewer_comments = (
        review_in.reviewer_comments
    )

    review.final_verdict = (
        review_in.final_verdict
    )

    review.updated_at = get_datetime_utc()

    submission = session.get(
        Submission,
        review.submission_id,
    )

    if (
        review_in.final_verdict
        == HumanReviewStatus.PASSED
    ):
        submission.human_reviewer = (
            SubmissionStatus.PASSED
        )
    else:
        submission.human_reviewer = (
            SubmissionStatus.REJECTED
        )

    submission.updated_at = get_datetime_utc()

    session.add(review)
    session.add(submission)

    session.commit()
    session.refresh(review)

    return review