from typing import Any

import requests
from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import SessionDep
from app.core.config import settings
from app.models import (
    Assessment,
    DEFAULT_SUBMISSION_ID,
    Submission,
    SubmissionCreate,
    SubmissionPublic,
    SubmissionStatusUpdate,
    SubmissionTriggerResponse,
    get_datetime_utc,
)


router = APIRouter(tags=["submission"])


@router.post("/submit", response_model=SubmissionTriggerResponse)
def submit_assessment(
    submission_in: SubmissionCreate,
    session: SessionDep,
) -> Any:
    statement = select(Assessment.attachment_object_name).where(
        Assessment.id == submission_in.assessment_id
    )
    rows = session.exec(statement).all()
    if not rows:
        raise HTTPException(status_code=404, detail="Assessment not found")
    object_name = rows[0]
    print(f"Retrieved object_name from DB: {object_name}")
    if not object_name:
        raise HTTPException(
            status_code=400, detail="Assessment attachment is not uploaded yet"
        )

    submission = session.get(Submission, DEFAULT_SUBMISSION_ID)
    if submission:
        submission.assessment_id = submission_in.assessment_id
        submission.updated_at = get_datetime_utc()
    else:
        submission = Submission(assessment_id=submission_in.assessment_id)

    session.add(submission)
    session.commit()
    session.refresh(submission)

    # if not settings.TIER1_SERVICE_TOKEN:
    #     raise HTTPException(
    #         status_code=500,
    #         detail="TIER1_SERVICE_TOKEN is not configured",
    #     )

    # payload = {
    #     "submission_id": str(submission.id),
    #     "assessment_id": str(submission.assessment_id),
    #     "level": 1,
    #     "attempt_number": 1,
    #     "zip_storage_key": object_name,
    #     "agent_type": "standard",
    #     "rubric_version": "rubv_001",
    # }

    # try:
    #     response = requests.post(
    #         settings.TIER1_JOB_URL,
    #         headers={
    #             "Authorization": f"Bearer {settings.TIER1_SERVICE_TOKEN}",
    #             "Content-Type": "application/json",
    #         },
    #         json=payload,
    #         timeout=30,
    #     )
    #     try:
    #         response_body = response.json()
    #     except ValueError:
    #         response_body = response.text
    #     response.raise_for_status()
    # except requests.RequestException as exc:
    #     detail = (
    #         response_body
    #         if "response_body" in locals()
    #         else f"Failed to trigger external submission service: {exc}"
    #     )
    #     raise HTTPException(status_code=502, detail=detail) from exc

    return SubmissionTriggerResponse(
        submission_id=submission.id,
        assessment_id=submission.assessment_id,
        status_code=200,
        response={"message": "Submission triggered successfully (mock response)"},
        # status_code=response.status_code,
        # response=response_body,
    )


@router.get("/submissions/{id}", response_model=SubmissionPublic)
def read_submission(id: str, session: SessionDep) -> Any:
    submission = session.get(Submission, id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


@router.patch("/submissions/{id}/status", response_model=SubmissionPublic)
def update_submission_status(
    id: str,
    submission_in: SubmissionStatusUpdate,
    session: SessionDep,
) -> Any:
    submission = session.get(Submission, id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    update_data = submission_in.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No status fields provided")

    submission.sqlmodel_update(update_data)
    submission.updated_at = get_datetime_utc()

    session.add(submission)
    session.commit()
    session.refresh(submission)
    return submission
