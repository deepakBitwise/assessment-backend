from datetime import timedelta
from typing import Any
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from app.api.deps import SessionDep
from app.core.config import settings
from app.core.minio_config import minio_client
from app.models import Assessment, AssessmentAttachmentUpdate, get_datetime_utc

logger = logging.getLogger(__name__)


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
    logger.info(f"📤 Upload URL request - Assessment ID: {data.assessment_id}, Filename: {data.filename}")
    
    assessment = session.get(Assessment, data.assessment_id)
    if not assessment:
        logger.error(f"❌ Assessment not found: {data.assessment_id}")
        raise HTTPException(status_code=404, detail="Assessment not found")

    object_name = f"assessments/{assessment.id}/attachments/{data.filename}"
    logger.debug(f"📝 Object name generated: {object_name}")

    try:
        logger.info(f"🔗 Generating presigned upload URL for object: {object_name}")
        url = minio_client.presigned_put_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            expires=timedelta(minutes=15),
        )
        logger.info(f"✅ Presigned upload URL generated successfully")
    except Exception as exc:
        logger.error(f"❌ Failed to generate upload URL: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        logger.info(f"💾 Updating assessment attachment metadata for: {data.assessment_id}")
        assessment.sqlmodel_update(
            AssessmentAttachmentUpdate(attachment_object_name=object_name).model_dump()
        )
        assessment.updated_at = get_datetime_utc()
        session.add(assessment)
        session.commit()
        logger.info(f"✅ Assessment metadata updated successfully")
    except Exception as exc:
        logger.error(f"❌ Failed to update assessment metadata: {str(exc)}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    logger.info(f"✨ Upload URL generation complete - Ready for file upload to: {object_name}")
    return {
        "upload_url": url,
        "object_name": object_name,
    }


@router.get("/download-url/{object_name:path}")
def generate_download_url(object_name: str) -> Any:
    logger.info(f"📥 Download URL request - Object: {object_name}")
    try:
        url = minio_client.presigned_get_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            expires=timedelta(minutes=15),
        )
        logger.info(f"✅ Download URL generated successfully for: {object_name}")
    except Exception as exc:
        logger.error(f"❌ Failed to generate download URL for {object_name}: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "download_url": url,
    }


@router.get("/assessment/{assessment_id}/download-url")
def generate_assessment_download_url(
    assessment_id: str,
    session: SessionDep,
) -> Any:
    logger.info(f"📥 Assessment download URL request - Assessment ID: {assessment_id}")
    statement = select(Assessment.attachment_object_name).where(Assessment.id == assessment_id)
    rows = session.exec(statement).all()
    if not rows:
        logger.error(f"❌ Assessment not found: {assessment_id}")
        raise HTTPException(status_code=404, detail="Assessment not found")
    object_name = rows[0]
    if not object_name:
        logger.error(f"❌ Assessment attachment not found for: {assessment_id}")
        raise HTTPException(status_code=404, detail="Assessment attachment not found")

    logger.debug(f"📝 Object name: {object_name}")
    try:
        url = minio_client.presigned_get_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            expires=timedelta(minutes=15),
        )
        logger.info(f"✅ Assessment download URL generated successfully")
    except Exception as exc:
        logger.error(f"❌ Failed to generate assessment download URL: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "object_name": object_name,
        "download_url": url,
    }
