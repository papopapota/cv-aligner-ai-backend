from unittest.mock import AsyncMock

import pytest

from src.application.ports.inbound.upload_cv_use_case import (
    FileUpload,
    UploadCVUseCase,
)
from src.application.ports.out.cv_parser_port import CVParserPort
from src.application.services.upload_cv_service import UploadCVService
from src.domain.errors import UnsupportedFormatError
from src.domain.job_description import JobDescription
from src.domain.uploaded_file_metadata import UploadedFileMetadata

_CONTENT = b"%PDF-1.7 fake cv bytes"
_EXTRACTED_TEXT = "Python developer with 5 years of experience in FastAPI."
_JOB_DESCRIPTION = "We are looking for a Python developer with FastAPI experience."


@pytest.fixture
def cv_parser() -> AsyncMock:
    parser = AsyncMock(spec=CVParserPort)
    parser.parse.return_value = _EXTRACTED_TEXT
    return parser


@pytest.fixture
def service(cv_parser: AsyncMock) -> UploadCVService:
    return UploadCVService(cv_parser)


def _upload(filename: str = "cv.pdf") -> FileUpload:
    return FileUpload(
        filename=filename,
        content_type="application/pdf",
        content=_CONTENT,
    )


def _job_description() -> JobDescription:
    return JobDescription(raw_text=_JOB_DESCRIPTION)


async def test_returns_a_candidate_cv_with_the_parsed_text(
    service: UploadCVService,
) -> None:
    candidate = await service.execute(_upload(), _job_description())

    assert candidate.raw_text == _EXTRACTED_TEXT


async def test_derives_the_metadata_from_the_uploaded_bytes(
    service: UploadCVService,
) -> None:
    candidate = await service.execute(_upload(), _job_description())

    assert candidate.metadata == UploadedFileMetadata.from_bytes(
        "cv.pdf",
        "application/pdf",
        _CONTENT,
    )


async def test_calls_the_parser_with_the_filename_and_the_content(
    service: UploadCVService,
    cv_parser: AsyncMock,
) -> None:
    upload = _upload()

    await service.execute(upload, _job_description())

    cv_parser.parse.assert_awaited_once_with("cv.pdf", _CONTENT)


async def test_does_not_parse_when_the_upload_is_invalid(
    service: UploadCVService,
    cv_parser: AsyncMock,
) -> None:
    with pytest.raises(UnsupportedFormatError):
        await service.execute(_upload("cv.txt"), _job_description())

    cv_parser.parse.assert_not_awaited()


async def test_propagates_the_parser_error(
    service: UploadCVService,
    cv_parser: AsyncMock,
) -> None:
    cv_parser.parse.side_effect = RuntimeError("corrupted pdf")

    with pytest.raises(RuntimeError, match="corrupted pdf"):
        await service.execute(_upload(), _job_description())


async def test_satisfies_the_inbound_port(service: UploadCVService) -> None:
    candidate = await service.execute(_upload(), _job_description())

    assert isinstance(service, UploadCVUseCase)
    assert isinstance(candidate.raw_text, str)