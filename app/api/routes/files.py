##app/api/routes/files.py
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from app.api.deps import SessionDep
from app.core.config import settings
from app.core.minio_config import minio_client
from app.models import Assessment, AssessmentAttachmentUpdate, get_datetime_utc


router = APIRouter(prefix="/files", tags=["files"])


class UploadRequest(BaseModel):
    filename: str
    content_type: str
    assessment_id: str


@router.post("/upload-url")
def generate_upload_url(
    data: UploadRequest,
    session: SessionDep,
) -> Any:
    assessment = session.get(Assessment, data.assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    object_name = f"assessments/{assessment.id}/attachments/{data.filename}"

    try:
        url = minio_client.presigned_put_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            expires=timedelta(minutes=15),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    assessment.sqlmodel_update(
        AssessmentAttachmentUpdate(attachment_object_name=object_name).model_dump()
    )
    assessment.updated_at = get_datetime_utc()
    session.add(assessment)
    session.commit()

    return {
        "upload_url": url,
        "object_name": object_name,
    }


@router.get("/download-url/{object_name:path}")
def generate_download_url(object_name: str) -> Any:
    try:
        url = minio_client.presigned_get_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            expires=timedelta(minutes=15),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "download_url": url,
    }


@router.get("/assessment/{assessment_id}/download-url")
def generate_assessment_download_url(
    assessment_id: str,
    session: SessionDep,
) -> Any:
    statement = select(Assessment.attachment_object_name).where(Assessment.id == assessment_id)
    rows = session.exec(statement).all()
    if not rows:
        raise HTTPException(status_code=404, detail="Assessment not found")
    object_name = rows[0]
    if not object_name:
        raise HTTPException(status_code=404, detail="Assessment attachment not found")

    try:
        url = minio_client.presigned_get_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            expires=timedelta(minutes=15),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "object_name": object_name,
        "download_url": url,
    }
