from typing import Any

from fastapi import APIRouter, Header, HTTPException, status
from sqlmodel import select

from app.api.deps import SessionDep
from app.core.config import settings
from app.models import (
    LLMJudgeResult,
    LLMJudgeResultCreate,
    LLMJudgeResultPublic,
    Submission,
    SubmissionEventCreate,
    SubmissionEventType,
    SubmissionEvents,
    SubmissionStatus,
    get_datetime_utc,
)

router = APIRouter(tags=["llm-judge"])


def _verify_service_token(x_service_token: str | None) -> None:
    if not settings.LLM_JUDGE_SERVICE_TOKEN:
        return
    if x_service_token != settings.LLM_JUDGE_SERVICE_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing service token",
        )


def _append_submission_event(
    session,
    submission_id: str,
    event_type: SubmissionEventType,
    value: str,
    now,
) -> None:
    statement = select(SubmissionEvents).where(
        SubmissionEvents.submission_id == submission_id
    )
    submission_events = session.exec(statement).first()
    event = SubmissionEventCreate(type=event_type, value=value, timestamp=now)

    if submission_events:
        submission_events.events = [
            *submission_events.events,
            event.model_dump(mode="json"),
        ]
    else:
        submission_events = SubmissionEvents(
            id=submission_id,
            submission_id=submission_id,
            events=[event.model_dump(mode="json")],
        )
    session.add(submission_events)


@router.post(
    "/llm-judge/results",
    response_model=LLMJudgeResultPublic,
    status_code=status.HTTP_201_CREATED,
)
def submit_llm_judge_result(
    result_in: LLMJudgeResultCreate,
    session: SessionDep,
    x_service_token: str | None = Header(default=None),
) -> Any:
    # _verify_service_token(x_service_token)

    submission = session.get(Submission, result_in.submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    statement = select(LLMJudgeResult).where(
        LLMJudgeResult.submission_id == result_in.submission_id
    )
    existing = session.exec(statement).first()

    now = get_datetime_utc()
    data = result_in.model_dump(mode="json")

    if existing:
        existing.sqlmodel_update(data)
        existing.updated_at = now
        result = existing
    else:
        result = LLMJudgeResult(
            id=f"{result_in.submission_id}-llm-judge",
            **data,
            created_at=now,
            updated_at=now,
        )
    session.add(result)

    verdict = result_in.provisional_verdict.upper()
    print(f"Verdict : {verdict}")
    if verdict == "PASSED":
        submission.llm_judge = SubmissionStatus.PASSED
    elif verdict == "REJECTED":
        submission.llm_judge = SubmissionStatus.REJECTED
    else:
        submission.llm_judge = SubmissionStatus.QUEUED
    submission.updated_at = now
    session.add(submission)

    event_type = (
        SubmissionEventType.SUCCESS
        if verdict == "PASSED"
        else SubmissionEventType.FAILURE
    )
    event_value = (
        f"LLM judge verdict: {verdict}. "
        f"Final score: {result_in.final_score}/{result_in.final_score_max}"
    )
    # _append_submission_event(session, result_in.submission_id, event_type, event_value, now)

    session.commit()
    session.refresh(result)
    return result


@router.get(
    "/llm-judge/results/{submission_id}",
    response_model=LLMJudgeResultPublic,
)
def get_llm_judge_result(
    submission_id: str,
    session: SessionDep,
) -> Any:
    print("Checking results")  
    statement = select(LLMJudgeResult).where(
        LLMJudgeResult.submission_id == submission_id
    )
    result = session.exec(statement).first()
    if not result:
        raise HTTPException(
            status_code=404,
            detail="LLM judge result not found for this submission",
        )
    return result
