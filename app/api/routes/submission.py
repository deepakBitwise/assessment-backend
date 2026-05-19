from typing import Any
from uuid import uuid4
import requests
import logging

from fastapi import APIRouter, Body, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.core.config import settings

from app.api.deps import SessionDep
from app.models import (
    Assessment,
    Submission,
    SubmissionCreate,
    SubmissionEventType,
    SubmissionEvents,
    SubmissionEventsPublic,
    SubmissionPublic,
    SubmissionStatus,
    SubmissionStatusUpdate,
    SubmissionTriggerResponse,
    get_datetime_utc,
)

logger = logging.getLogger(__name__)


router = APIRouter(tags=["submission"])


def _status_from_tier1_result(result: dict[str, Any]) -> SubmissionStatusUpdate:
    tier_status = str(result.get("tier1_status") or result.get("status") or "").lower()
    all_required_passed = result.get("all_required_passed")

    if tier_status in {"passed", "pass", "accepted", "success"} or all_required_passed is True:
        return SubmissionStatusUpdate(automated_check=SubmissionStatus.PASSED)

    if tier_status in {"rejected", "failed", "failure", "error"} or all_required_passed is False:
        return SubmissionStatusUpdate(automated_check=SubmissionStatus.REJECTED)

    return SubmissionStatusUpdate(automated_check=SubmissionStatus.QUEUED)


def _event_from_payload(event_in: dict[str, Any]) -> dict[str, str]:
    event_type = event_in.get("type") or event_in.get("event_type") or "GENERAL"
    value = (
        event_in.get("value")
        or event_in.get("message")
        or event_in.get("error")
        or event_in.get("reason")
        or event_in.get("event")
        or "Tier 1 event received"
    )

    normalized_type = str(event_type).upper()
    if normalized_type not in {item.value for item in SubmissionEventType}:
        normalized_type = SubmissionEventType.GENERAL.value

    return {"type": normalized_type, "value": str(value)[:2048]}


@router.post("/submit", response_model=SubmissionTriggerResponse)
def submit_assessment(
    submission_in: SubmissionCreate,
    session: SessionDep,
) -> Any:
    logger.info(f"🎯 Submission request received - Assessment ID: {submission_in.assessment_id}, Attempt: {submission_in.attempt_number}")
    
    # Step 1: Retrieve assessment attachment
    statement = select(Assessment.attachment_object_name).where(
        Assessment.id == submission_in.assessment_id
    )
    rows = session.exec(statement).all()
    if not rows:
        logger.error(f"❌ Assessment not found: {submission_in.assessment_id}")
        raise HTTPException(status_code=404, detail="Assessment not found")
    object_name = rows[0]
    logger.info(f"📦 Retrieved attachment from database - Object Name: {object_name}")
    
    if not object_name:
        logger.error(f"❌ Assessment attachment not uploaded yet for: {submission_in.assessment_id}")
        raise HTTPException(
            status_code=400, detail="Assessment attachment is not uploaded yet"
        )

    try:
        # Step 2: Generate a stable unique submission ID for repeat test runs.
        new_id = f"submission-{uuid4().hex[:12]}"
        logger.debug(f"📊 New submission ID generated: {new_id}")

        # Step 3: Create submission record
        logger.info(f"💾 Creating submission record - ID: {new_id}, Assessment: {submission_in.assessment_id}")
        submission = Submission(
            id=new_id,
            assessment_id=submission_in.assessment_id,
            attachment_object_name=object_name,
        )

        # Step 4: Save to database
        logger.info(f"🔄 Saving submission to database...")
        session.add(submission)
        session.commit()
        session.refresh(submission)
        logger.info(f"✅ Submission saved successfully - ID: {submission.id}, Created at: {submission.created_at}")
        
    except IntegrityError as e:
        session.rollback()
        logger.error(f"❌ Integrity Error - Submission ID {new_id} already exists: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Submission ID {new_id} already exists. Please try again."
        )
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Database error while saving submission: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while saving the submission."
        )

    # Step 5: Prepare tier 1 evaluation payload
    logger.debug(f"🔧 Preparing tier 1 evaluation payload...")
    payload = {
        "submission_id": str(submission.id),
        "assessment_id": str(submission.assessment_id),
        "level": 1,
        "attempt_number": submission_in.attempt_number,
        "zip_storage_key": object_name,
        "agent_type": "standard",
        "rubric_version": "rubv_001",
    }
    logger.debug(f"📋 Payload prepared: {payload}")

    try:
        # Step 6: Trigger tier 1 evaluation
        logger.info(f"🚀 Triggering tier 1 evaluation - URL: {settings.TIER1_JOB_URL}")
        logger.info(f"📤 Sending submission to tier 1 service...")
        response = requests.post(
            settings.TIER1_JOB_URL,
            headers={
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        try:
            response_body = response.json()
        except ValueError:
            response_body = response.text
        
        logger.info(f"📥 Tier 1 service response - Status: {response.status_code}")
        logger.debug(f"Response body: {response_body}")
        response.raise_for_status()
        logger.info(f"✅ Tier 1 evaluation triggered successfully - Submission: {submission.id}")
        
    except requests.RequestException as exc:
        detail = (
            response_body
            if "response_body" in locals()
            else f"Failed to trigger external submission service: {exc}"
        )
        logger.error(f"❌ Failed to trigger tier 1 evaluation: {detail}", exc_info=True)
        raise HTTPException(status_code=502, detail=detail) from exc

    logger.info(f"🎉 Submission workflow complete - Submission ID: {submission.id}")
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
    logger.info(f"📋 Fetching submission details - ID: {id}")
    submission = session.get(Submission, id)
    if not submission:
        logger.error(f"❌ Submission not found: {id}")
        raise HTTPException(status_code=404, detail="Submission not found")
    logger.info(f"✅ Submission retrieved - Status: {submission.status}")
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
    logger.info(f"📊 Fetching submissions - Offset: {offset}, Limit: {limit}")
    statement = select(Submission).offset(offset).limit(limit)
    submissions = session.exec(statement).all()
    logger.info(f"✅ Retrieved {len(submissions)} submissions")
    return submissions

@router.patch("/submissions/{id}/status", response_model=SubmissionPublic)
def update_submission_status(
    id: str,
    submission_in: SubmissionStatusUpdate,
    session: SessionDep,
) -> Any:
    logger.info(f"🔄 Updating submission status - ID: {id}")
    submission = session.get(Submission, id)
    if not submission:
        logger.error(f"❌ Submission not found: {id}")
        raise HTTPException(status_code=404, detail="Submission not found")

    update_data = submission_in.model_dump(exclude_unset=True)
    if not update_data:
        logger.warning(f"⚠️ No status fields provided for: {id}")
        raise HTTPException(status_code=400, detail="No status fields provided")

    logger.debug(f"📝 Update data: {update_data}")
    submission.sqlmodel_update(update_data)
    submission.updated_at = get_datetime_utc()

    session.add(submission)
    session.commit()
    session.refresh(submission)
    logger.info(f"✅ Submission status updated - New Status: {submission.status}")
    return submission


@router.post("/submissions/{id}/tier1_results", response_model=SubmissionPublic)
def write_tier1_results(
    id: str,
    session: SessionDep,
    result: dict[str, Any] = Body(...),
) -> Any:
    logger.info(f"🧪 Writing tier 1 results - Submission ID: {id}")
    submission = session.get(Submission, id)
    if not submission:
        logger.error(f"❌ Submission not found for tier 1 results: {id}")
        raise HTTPException(status_code=404, detail="Submission not found")

    status_update = _status_from_tier1_result(result)
    update_data = status_update.model_dump(exclude_unset=True)

    submission.sqlmodel_update(update_data)
    submission.updated_at = get_datetime_utc()

    session.add(submission)
    session.commit()
    session.refresh(submission)
    logger.info(
        f"✅ Tier 1 results stored - Submission: {submission.id}, Automated check: {submission.automated_check}"
    )
    return submission


@router.post(
    "/submission/{submission_id}/events",
    response_model=SubmissionEventsPublic,
)
def create_submission_events(
    submission_id: str,
    session: SessionDep,
    event_in: dict[str, Any] = Body(...),
) -> Any:
    event_payload = _event_from_payload(event_in)
    logger.info(f"📝 Creating submission event - Submission ID: {submission_id}, Event: {event_payload['type']}")
    submission = session.get(Submission, submission_id)
    if not submission:
        logger.error(f"❌ Submission not found: {submission_id}")
        raise HTTPException(status_code=404, detail="Submission not found")

    statement = select(SubmissionEvents).where(
        SubmissionEvents.submission_id == submission_id
    )
    submission_events = session.exec(statement).first()

    try:
        if submission_events:
            logger.debug(f"📌 Appending event to existing events record")
            submission_events.events = [
                *submission_events.events,
                event_payload,
            ]
        else:
            logger.debug(f"📌 Creating new events record")
            submission_events = SubmissionEvents(
                id=submission_id,
                submission_id=submission_id,
                events=[event_payload],
            )

        session.add(submission_events)
        session.commit()
        session.refresh(submission_events)
        logger.info(f"✅ Event saved successfully - Total events: {len(submission_events.events)}")
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Failed to save submission event: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save event")
    
    return SubmissionEventsPublic.model_validate(submission_events)


@router.get(
    "/submission/{submission_id}/events",
    response_model=SubmissionEventsPublic,
)
def read_submission_events(
    submission_id: str,
    session: SessionDep,
) -> Any:
    logger.info(f"📋 Fetching submission events - Submission ID: {submission_id}")
    statement = select(SubmissionEvents).where(
        SubmissionEvents.submission_id == submission_id
    )
    submission_events = session.exec(statement).first()
    if not submission_events:
        logger.warning(f"⚠️ No events found for submission: {submission_id}")
        raise HTTPException(status_code=404, detail="Submission events not found")

    logger.info(f"✅ Retrieved {len(submission_events.events)} events for submission: {submission_id}")
    return SubmissionEventsPublic.model_validate(submission_events)
