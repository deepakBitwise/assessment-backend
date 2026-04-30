from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings


class LocalStorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)

    def absolute_path(self, object_key: str) -> Path:
        candidate = (self.settings.upload_dir / object_key).resolve()
        root = self.settings.upload_dir.resolve()
        if root not in candidate.parents and candidate != root:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object key.")
        return candidate

    async def write_bytes(self, object_key: str, body: bytes) -> dict:
        path = self.absolute_path(object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        checksum = hashlib.sha256(body).hexdigest()
        return {"size_bytes": len(body), "checksum": checksum, "content_type": "application/octet-stream"}

    def describe(self, object_key: str) -> dict:
        path = self.absolute_path(object_key)
        if not path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uploaded object not found.")
        data = path.read_bytes()
        return {"size_bytes": len(data), "checksum": hashlib.sha256(data).hexdigest()}
