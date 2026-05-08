from datetime import timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
import requests
from app.core.minio_config import minio_client
from app.core.config import settings
from app.api.deps import SessionDep
from app.models import SubmissionFile


router = APIRouter(prefix="/files", tags=["files"])


class UploadRequest(BaseModel):
    filename: str
    content_type: str

    submission_id: str
    assessment_id: str

@router.post("/upload-url")
def generate_upload_url(
    data: UploadRequest,
    session: SessionDep,
):

    object_name = data.filename

    try:
        url = minio_client.presigned_put_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            expires=timedelta(minutes=15)
        )

        db_file = SubmissionFile(
            submission_id=data.submission_id,
            assessment_id=data.assessment_id,
            file_name=data.filename,
            object_key=object_name,
            bucket_name=settings.MINIO_BUCKET,
        )

        session.add(db_file)
        session.commit()
        session.refresh(db_file)

        return {
            "upload_url": url,
            "object_name": object_name
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download-url/{object_name}")
def generate_download_url(object_name: str):

    try:
        url = minio_client.presigned_get_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            expires=timedelta(minutes=15)
        )

        return {
            "download_url": url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/{submission_id}")
def get_uploaded_files(
    submission_id: str,
    session: SessionDep,
):
    files = session.query(SubmissionFile).filter(
        SubmissionFile.submission_id == submission_id
    ).all()

    return files


@router.post("/evaluate/{submission_id}")
def evaluate_submission(
    submission_id: str,
    session: SessionDep,
):

    files = session.query(SubmissionFile).filter(
        SubmissionFile.submission_id == submission_id
    ).all()

    if not files:
        raise HTTPException(
            status_code=404,
            detail="No files found"
        )

    file = files[0]

    payload = {
        "submission_id": file.submission_id,
        "assessment_id": file.assessment_id,
        "attempt_number": 1,
        "artifact_urls": {
            "solution": f"s3://{file.bucket_name}/{file.object_key}"
        },
        "required_deliverables": [
            "solution"
        ],
        "min_harness_pass_rate": 0.7,
        "test_cases": [],
        "entry_point_role": "solution",
        "tier2_webhook_url": ""
    }

    response = requests.post(
        "http://localhost:8080/jobs/tier1",
        json=payload
    )

    return {
        "status_code": response.status_code,
        "response": response.json()
    }