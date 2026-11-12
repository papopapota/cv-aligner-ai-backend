from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from src.application.ports.inbound.cv_upload_use_case import (
    CVUploadUseCase,
    FileUpload,
)
from src.application.ports.out.cv_repository_port import CVRepositoryPort
from src.application.ports.out.file_storage_port import FileStoragePort
from src.domain.cv_status import CVStatus
from src.domain.entities.cv import CV
from src.domain.errors import StorageError
from src.domain.uploaded_file_metadata import UploadedFileMetadata

logger = logging.getLogger(__name__)


class CVUploadService(CVUploadUseCase):
    def __init__(
        self,
        storage: FileStoragePort,
        repository: CVRepositoryPort,
    ) -> None:
        self._storage = storage
        self._repository = repository

    async def execute(self, cv: FileUpload, user_id: int) -> CV:
        metadata = UploadedFileMetadata.from_bytes(
            cv.filename,
            cv.content_type,
            cv.content,
        )
        cv_id = uuid4()
        extension = Path(metadata.filename).suffix.lower()
        s3_key = f"users/{user_id}/cvs/{cv_id}{extension}"

        await self._storage.upload(s3_key, cv.content, metadata.content_type)

        entity = CV(
            id=cv_id,
            user_id=user_id,
            s3_key=s3_key,
            filename=metadata.filename,
            content_type=metadata.content_type,
            size_bytes=metadata.size_bytes,
            sha256=metadata.sha256,
            status=CVStatus.UPLOADED,
        )
        try:
            return await self._repository.create(entity)
        except Exception:
            try:
                await self._storage.delete(s3_key)
            except StorageError:
                logger.exception("Could not roll back the uploaded object '%s'.", s3_key)
            raise
