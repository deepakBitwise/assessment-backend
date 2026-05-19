from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.api.deps import SessionDep
from app.models import (
    Assessment,
    Submission,
    SubmissionCreate,
    SubmissionEventCreate,
    SubmissionEvents,
    SubmissionEventsPublic,
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
    user_id = submission_in.user_id
    print(f"Received submission request for assessment_id: {submission_in.assessment_id} from user_id: {user_id}")
    print(f"Retrieved object_name from DB: {object_name}")
    if not object_name:
        raise HTTPException(
            status_code=400, detail="Assessment attachment is not uploaded yet"
        )

    try:
        # 1. Calculate the new ID
        # Using func.count() - note: this can be shaky if you delete records
        statement = select(func.count()).select_from(Submission)
        total_count = session.exec(statement).one()
        new_id = f"{user_id}-submission-{total_count + 1}"

        # 2. Instantiate the model
        submission = Submission(
            id=new_id,
            user_id=user_id,
            assessment_id=submission_in.assessment_id,
            attachment_object_name=object_name,
        )

        # 3. Transactional Save
        session.add(submission)
        session.commit()
        session.refresh(submission)
        
    except IntegrityError as e:
        # This triggers if 'new_id' already exists in the DB
        session.rollback()  # Crucial: Reset the session state
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Submission ID {new_id} already exists. Please try again."
        )
    except Exception as e:
        # Catch-all for database connection issues or other server errors
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while saving the submission."
        )

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

# Get unique submission by ID - useful for checking status after triggering
@router.get("/submissions/{id}", response_model=SubmissionPublic)
def read_submission(id: str, session: SessionDep) -> Any:
    submission = session.get(Submission, id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission

# Get all submissions with pagination - useful for listing and monitoring
@router.get("/submissions", response_model=list[SubmissionPublic])
def read_submissions(
    session: SessionDep, 
    offset: int = 0, 
    limit: int = Query(default=100, le=100)
) -> Any:
    """
    Retrieve all submissions.
    """
    print("Fetching all submissions...")
    statement = select(Submission).offset(offset).limit(limit)
    submissions = session.exec(statement).all()
    return submissions

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


@router.post(
    "/submission/{submission_id}/events",
    response_model=SubmissionEventsPublic,
)
def create_submission_events(
    submission_id: str,
    event_in: SubmissionEventCreate,
    session: SessionDep,
) -> Any:
    submission = session.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    statement = select(SubmissionEvents).where(
        SubmissionEvents.submission_id == submission_id
    )
    submission_events = session.exec(statement).first()

    if submission_events:
        submission_events.events = [
            *submission_events.events,
            event_in.model_dump(),
        ]
    else:
        submission_events = SubmissionEvents(
            id=submission_id,
            submission_id=submission_id,
            events=[event_in.model_dump()],
        )

    session.add(submission_events)
    session.commit()
    session.refresh(submission_events)
    return SubmissionEventsPublic.model_validate(submission_events)


@router.get(
    "/submission/{submission_id}/events",
    response_model=SubmissionEventsPublic,
)
def read_submission_events(
    submission_id: str,
    session: SessionDep,
) -> Any:
    statement = select(SubmissionEvents).where(
        SubmissionEvents.submission_id == submission_id
    )
    submission_events = session.exec(statement).first()
    if not submission_events:
        raise HTTPException(status_code=404, detail="Submission events not found")

    return SubmissionEventsPublic.model_validate(submission_events)
