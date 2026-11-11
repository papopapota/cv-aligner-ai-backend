from unittest.mock import AsyncMock

import pytest

from src.application.ports.inbound.cv_upload_use_case import (
    CVUploadUseCase,
    FileUpload,
)
from src.application.ports.out.cv_repository_port import CVRepositoryPort
from src.application.ports.out.file_storage_port import FileStoragePort
from src.application.services.cv_upload_service import CVUploadService
from src.domain.cv_status import CVStatus
from src.domain.entities.cv import CV
from src.domain.errors import EmptyContentError, StorageError, UnsupportedFormatError

_CONTENT = b"%PDF-1.7 fake cv bytes"
_USER_ID = 7


@pytest.fixture
def storage() -> AsyncMock:
    return AsyncMock(spec=FileStoragePort)


@pytest.fixture
def repository() -> AsyncMock:
    repository = AsyncMock(spec=CVRepositoryPort)
    repository.create.side_effect = lambda cv: cv
    return repository


@pytest.fixture
def service(storage: AsyncMock, repository: AsyncMock) -> CVUploadService:
    return CVUploadService(storage, repository)


def _upload(filename: str = "cv.pdf", content: bytes = _CONTENT) -> FileUpload:
    return FileUpload(
        filename=filename,
        content_type="application/pdf",
        content=content,
    )


async def test_stores_the_cv_and_returns_the_persisted_entity(
    service: CVUploadService,
    storage: AsyncMock,
    repository: AsyncMock,
) -> None:
    result = await service.execute(_upload(), _USER_ID)

    assert result.user_id == _USER_ID
    assert result.filename == "cv.pdf"
    assert result.content_type == "application/pdf"
    assert result.size_bytes == len(_CONTENT)
    assert result.status is CVStatus.UPLOADED
    assert result.s3_key.startswith(f"users/{_USER_ID}/cvs/")
    assert result.s3_key.endswith(".pdf")

    storage.upload.assert_awaited_once_with(
        result.s3_key,
        _CONTENT,
        "application/pdf",
    )
    repository.create.assert_awaited_once_with(result)


async def test_builds_a_unique_s3_key_per_upload(
    service: CVUploadService,
) -> None:
    first = await service.execute(_upload(), _USER_ID)
    second = await service.execute(_upload(), _USER_ID)

    assert first.id != second.id
    assert first.s3_key != second.s3_key


async def test_derives_the_metadata_from_the_uploaded_bytes(
    service: CVUploadService,
) -> None:
    result = await service.execute(_upload(), _USER_ID)

    assert result.filename == "cv.pdf"
    assert result.size_bytes == len(_CONTENT)
    assert len(result.sha256) == 64


async def test_does_not_store_an_unsupported_extension(
    service: CVUploadService,
    storage: AsyncMock,
    repository: AsyncMock,
) -> None:
    with pytest.raises(UnsupportedFormatError):
        await service.execute(_upload("cv.txt"), _USER_ID)

    storage.upload.assert_not_awaited()
    repository.create.assert_not_awaited()


async def test_does_not_store_empty_content(
    service: CVUploadService,
    storage: AsyncMock,
    repository: AsyncMock,
) -> None:
    with pytest.raises(EmptyContentError):
        await service.execute(_upload(content=b""), _USER_ID)

    storage.upload.assert_not_awaited()
    repository.create.assert_not_awaited()


async def test_deletes_the_object_when_persistence_fails(
    service: CVUploadService,
    storage: AsyncMock,
    repository: AsyncMock,
) -> None:
    repository.create.side_effect = RuntimeError("database down")

    with pytest.raises(RuntimeError, match="database down"):
        await service.execute(_upload(), _USER_ID)

    s3_key = storage.upload.await_args.args[0]
    storage.delete.assert_awaited_once_with(s3_key)


async def test_does_not_mask_the_original_error_when_rollback_fails(
    service: CVUploadService,
    storage: AsyncMock,
    repository: AsyncMock,
) -> None:
    repository.create.side_effect = RuntimeError("database down")
    storage.delete.side_effect = StorageError("s3 down")

    with pytest.raises(RuntimeError, match="database down"):
        await service.execute(_upload(), _USER_ID)


async def test_satisfies_the_inbound_port(service: CVUploadService) -> None:
    result = await service.execute(_upload(), _USER_ID)

    assert isinstance(service, CVUploadUseCase)
    assert isinstance(result, CV)
