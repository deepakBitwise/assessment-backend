from minio import Minio

from app.core.config import settings


minio_client = Minio(
    endpoint=settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE,
)


def create_bucket_if_not_exists():
    found = minio_client.bucket_exists(settings.MINIO_BUCKET)

    if not found:
        minio_client.make_bucket(settings.MINIO_BUCKET)