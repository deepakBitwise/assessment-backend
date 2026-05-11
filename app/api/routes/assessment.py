from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import SessionDep
from app.models import (
    Assessment,
    AssessmentCreate,
    AssessmentsPublic,
    AssessmentPublic,
    AssessmentUpdate,
    DEFAULT_ASSESSMENT_ID,
    get_datetime_utc,
)


router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.get("/", response_model=AssessmentsPublic)
def list_assessments(session: SessionDep) -> Any:
    assessments = session.exec(select(Assessment)).all()
    assessments_public = [
        AssessmentPublic.model_validate(assessment) for assessment in assessments
    ]
    return AssessmentsPublic(data=assessments_public, count=len(assessments_public))


@router.post("/", response_model=AssessmentPublic)
def create_assessment(
    assessment_in: AssessmentCreate,
    session: SessionDep,
) -> Any:
    assessment = session.get(Assessment, DEFAULT_ASSESSMENT_ID)
    if assessment:
        assessment.problem_statement = assessment_in.problem_statement
        assessment.deliverables = assessment_in.deliverables
        assessment.attachment_object_name = assessment_in.attachment_object_name
        assessment.updated_at = get_datetime_utc()
    else:
        assessment = Assessment.model_validate(assessment_in)
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return assessment


@router.get("/{id}", response_model=AssessmentPublic)
def read_assessment(id: str, session: SessionDep) -> Any:
    print(f"Fetching assessment with id: {id}")
    assessment = session.get(Assessment, id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment 


@router.put("/{id}", response_model=AssessmentPublic)
def update_assessment(
    id: str,
    assessment_in: AssessmentUpdate,
    session: SessionDep,
) -> Any:
    assessment = session.get(Assessment, id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    assessment.problem_statement = assessment_in.problem_statement
    assessment.deliverables = assessment_in.deliverables
    assessment.updated_at = get_datetime_utc()

    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return assessment
