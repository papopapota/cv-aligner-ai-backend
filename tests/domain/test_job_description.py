import dataclasses

import pytest

from src.domain.errors import EmptyContentError, UnsupportedFormatError
from src.domain.job_description import JobDescription
from src.domain.uploaded_file_metadata import UploadedFileMetadata

_RAW_TEXT = "We are looking for a Python developer with FastAPI experience."
_JD_METADATA = UploadedFileMetadata.from_job_description_bytes(
    filename="job.txt",
    content_type="text/plain",
    content=_RAW_TEXT.encode("utf-8"),
)


def test_create_job_description() -> None:
    description = JobDescription(metadata=_JD_METADATA, raw_text=_RAW_TEXT)

    assert description.raw_text == _RAW_TEXT
    assert description.metadata == _JD_METADATA


@pytest.mark.parametrize("raw_text", ["", "   ", "\n\t "])
def test_rejects_blank_raw_text(raw_text: str) -> None:
    metadata = UploadedFileMetadata.from_job_description_bytes(
        filename="job.txt",
        content_type="text/plain",
        content=b"dummy",
    )
    with pytest.raises(EmptyContentError):
        JobDescription(metadata=metadata, raw_text=raw_text)


def test_rejects_invalid_extension() -> None:
    metadata = UploadedFileMetadata.from_bytes(
        filename="job.pdf",
        content_type="application/pdf",
        content=b"dummy",
    )
    with pytest.raises(UnsupportedFormatError) as exc_info:
        JobDescription(metadata=metadata, raw_text=_RAW_TEXT)
    assert "txt" in str(exc_info.value).lower()


def test_is_immutable() -> None:
    description = JobDescription(metadata=_JD_METADATA, raw_text=_RAW_TEXT)

    with pytest.raises(dataclasses.FrozenInstanceError):
        description.raw_text = "another offer"  # type: ignore[misc]