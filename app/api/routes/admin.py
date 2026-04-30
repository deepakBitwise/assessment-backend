from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import admin_user, db_session
from app.models import Assessment, Attempt, Cohort, Submission, User, Verdict
from app.schemas import AssessmentPublishRequest

router = APIRouter(tags=["admin"])


@router.get("/admin/cohorts/{cohort_slug}/metrics")
async def cohort_metrics(
    cohort_slug: str,
    user: User = Depends(admin_user),
    session: AsyncSession = Depends(db_session),
) -> dict:
    cohort = await session.scalar(select(Cohort).where(Cohort.slug == cohort_slug))
    if cohort is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found.")

    total_submissions = await session.scalar(
        select(func.count(Submission.id)).join(Submission.attempt).join(Attempt.user).where(User.cohort_id == cohort.id)
    )
    passed = await session.scalar(
        select(func.count(Verdict.id))
        .join(Verdict.submission)
        .join(Submission.attempt)
        .join(Attempt.user)
        .where(User.cohort_id == cohort.id, Verdict.state == "passed")
    )
    return {
        "cohort": cohort.slug,
        "rubric_version": cohort.rubric_version,
        "submission_count": total_submissions or 0,
        "passed_count": passed or 0,
        "pass_rate": round((passed or 0) / total_submissions, 2) if total_submissions else 0.0,
    }


@router.post("/admin/assessments/{assessment_id}/publish")
async def publish_assessment(
    assessment_id: str,
    payload: AssessmentPublishRequest,
    user: User = Depends(admin_user),
    session: AsyncSession = Depends(db_session),
) -> dict:
    assessment = await session.scalar(select(Assessment).where(Assessment.public_id == assessment_id))
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")
    assessment.is_published = payload.activate
    await session.commit()
    return {"assessment_id": assessment.public_id, "published": assessment.is_published}
