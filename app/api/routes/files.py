from datetime import timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.minio_config import minio_client
from app.core.config import settings

router = APIRouter(prefix="/files", tags=["files"])


class UploadRequest(BaseModel):
    filename: str
    content_type: str


@router.post("/upload-url")
def generate_upload_url(data: UploadRequest):

    object_name = data.filename

    try:
        url = minio_client.presigned_put_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            expires=timedelta(minutes=15)
        )

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