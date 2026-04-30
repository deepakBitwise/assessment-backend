from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import current_user, db_session, learner_user
from app.core.security import new_public_id
from app.models import Artifact, Attempt, AuditEvent, Submission, UploadGrant, User
from app.schemas import (
    SubmissionCreateRequest,
    SubmissionDetail,
    SubmissionResponse,
    UploadPresignRequest,
    UploadPresignResponse,
)
from app.services.evaluation import evaluate_submission
from app.services.storage import LocalStorageService

router = APIRouter(tags=["submissions"])
storage = LocalStorageService()


@router.post("/uploads/presign", response_model=UploadPresignResponse)
async def presign_upload(
    payload: UploadPresignRequest,
    request: Request,
    user: User = Depends(learner_user),
    session: AsyncSession = Depends(db_session),
) -> UploadPresignResponse:
    attempt = await session.scalar(select(Attempt).where(Attempt.public_id == payload.attempt_id, Attempt.user_id == user.id))
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found.")

    token = new_public_id("upl")
    object_key = f"{attempt.public_id}/{token}/{payload.filename}"
    grant = UploadGrant(
        token=token,
        attempt_public_id=attempt.public_id,
        object_key=object_key,
        filename=payload.filename,
        content_type=payload.content_type,
    )
    session.add(grant)
    session.add(AuditEvent(actor_public_id=user.public_id, entity_ref=attempt.public_id, kind="upload.presigned", payload={"object_key": object_key}))
    await session.commit()
    return UploadPresignResponse(upload_token=token, upload_url=str(request.base_url) + f"uploads/{token}", object_key=object_key)


@router.put("/uploads/{upload_token}", status_code=status.HTTP_204_NO_CONTENT)
async def upload_object(
    upload_token: str,
    body: bytes = Body(...),
    session: AsyncSession = Depends(db_session),
) -> Response:
    grant = await session.scalar(select(UploadGrant).where(UploadGrant.token == upload_token))
    if grant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload grant not found.")
    await storage.write_bytes(grant.object_key, body)
    grant.uploaded = True
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/attempts/{attempt_id}/submissions", response_model=SubmissionResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_submission(
    attempt_id: str,
    payload: SubmissionCreateRequest,
    user: User = Depends(learner_user),
    session: AsyncSession = Depends(db_session),
) -> SubmissionResponse:
    attempt = await session.scalar(
        select(Attempt)
        .where(Attempt.public_id == attempt_id, Attempt.user_id == user.id)
        .options(selectinload(Attempt.assessment), selectinload(Attempt.submission))
    )
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found.")
    if attempt.submission is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Submission already exists for this attempt.")

    artifacts: list[Artifact] = []
    for artifact_ref in payload.artifacts:
        grant = await session.scalar(select(UploadGrant).where(UploadGrant.object_key == artifact_ref.object_key))
        if grant is None or not grant.uploaded:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Upload missing for {artifact_ref.object_key}")
        metadata = storage.describe(artifact_ref.object_key)
        artifacts.append(
            Artifact(
                public_id=new_public_id("art"),
                role=artifact_ref.role,
                filename=grant.filename,
                object_key=artifact_ref.object_key,
                content_type=grant.content_type,
                size_bytes=metadata["size_bytes"],
                checksum=metadata["checksum"],
            )
        )

    submission = Submission(
        public_id=new_public_id("sub"),
        attempt_id=attempt.id,
        status="queued",
        app_url=str(payload.live_app.url) if payload.live_app else None,
        dify_app_id=payload.live_app.dify_app_id if payload.live_app else None,
        encrypted_api_key=payload.live_app.api_key_ciphertext if payload.live_app else None,
    )
    attempt.state = "submitted"
    attempt.submitted_at = submission.submitted_at
    submission.artifacts = artifacts
    session.add(submission)
    session.add(AuditEvent(actor_public_id=user.public_id, entity_ref=submission.public_id, kind="submission.created", payload={"attempt_id": attempt.public_id}))
    await session.commit()

    refreshed = await session.scalar(
        select(Submission)
        .where(Submission.id == submission.id)
        .options(selectinload(Submission.artifacts), selectinload(Submission.attempt).selectinload(Attempt.assessment))
    )
    await evaluate_submission(session, refreshed)
    return SubmissionResponse(submission_id=submission.public_id, status=refreshed.status)


@router.get("/submissions/{submission_id}", response_model=SubmissionDetail)
async def get_submission(
    submission_id: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> SubmissionDetail:
    submission = await session.scalar(
        select(Submission)
        .where(Submission.public_id == submission_id)
        .options(
            selectinload(Submission.artifacts),
            selectinload(Submission.automated_run),
            selectinload(Submission.judge_runs),
            selectinload(Submission.reviews),
            selectinload(Submission.verdict),
            selectinload(Submission.attempt),
        )
    )
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    if user.role == "learner" and submission.attempt.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Submission not accessible.")

    return SubmissionDetail(
        submission_id=submission.public_id,
        attempt_id=submission.attempt.public_id,
        status=submission.status,
        submitted_at=submission.submitted_at,
        app_url=submission.app_url,
        artifacts=[
            {"id": artifact.public_id, "role": artifact.role, "filename": artifact.filename, "object_key": artifact.object_key}
            for artifact in submission.artifacts
        ],
        automated_run=submission.automated_run.checks if submission.automated_run else None,
        judge_runs=[{"run_no": run.run_no, "scores": run.scores, "confidence": run.confidence, "rationale": run.rationale} for run in submission.judge_runs],
        reviews=[{"decision": review.decision, "scores": review.scores, "notes": review.notes, "signed_at": review.signed_at} for review in submission.reviews],
        verdict={
            "state": submission.verdict.state,
            "weighted_score": submission.verdict.weighted_score,
            "dimension_scores": submission.verdict.dimension_scores,
            "reason": submission.verdict.reason,
        } if submission.verdict else None,
    )


@router.post("/submissions/{submission_id}/retry")
async def retry_submission(
    submission_id: str,
    user: User = Depends(learner_user),
    session: AsyncSession = Depends(db_session),
) -> dict:
    submission = await session.scalar(
        select(Submission)
        .where(Submission.public_id == submission_id)
        .options(selectinload(Submission.attempt), selectinload(Submission.verdict))
    )
    if submission is None or submission.attempt.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")
    if submission.verdict is None or submission.verdict.state != "failed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Retry is only available after a failed verdict.")
    submission.attempt.cooldown_until = submission.attempt.cooldown_until
    return {"message": "Create a new attempt after cooldown using POST /attempts."}
