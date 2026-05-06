from minio import Minio
from app.core.config import settings

minio_client = Minio(
    endpoint=settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=False  # True if using HTTPS
)

bucket = settings.MINIO_BUCKET

if not minio_client.bucket_exists(bucket):
    minio_client.make_bucket(bucket)