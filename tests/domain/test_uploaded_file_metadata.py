import dataclasses
import hashlib

import pytest

from src.domain import upload_rules
from src.domain.errors import (
    EmptyContentError,
    FileTooLargeError,
    InvalidUploadError,
    UnsupportedFormatError,
)
from src.domain.uploaded_file_metadata import UploadedFileMetadata

_CONTENT = b"%PDF-1.7 fake resume bytes"
_JOB_SPEC_CONTENT = "We are looking for a Python developer.".encode("utf-8")


def _metadata(**overrides: object) -> UploadedFileMetadata:
    fields: dict[str, object] = {
        "filename": "cv.pdf",
        "content_type": "application/pdf",
        "size_bytes": len(_CONTENT),
        "sha256": hashlib.sha256(_CONTENT).hexdigest(),
    }
    fields.update(overrides)
    return UploadedFileMetadata(**fields)


def test_from_bytes_derives_size_and_digest() -> None:
    metadata = UploadedFileMetadata.from_bytes(
        "cv.pdf",
        "application/pdf",
        _CONTENT,
    )

    assert metadata.size_bytes == len(_CONTENT)
    assert metadata.sha256 == hashlib.sha256(_CONTENT).hexdigest()


def test_from_bytes_keeps_the_given_filename_and_content_type() -> None:
    metadata = UploadedFileMetadata.from_bytes("cv.docx", "application/pdf", _CONTENT)

    assert metadata.filename == "cv.docx"
    assert metadata.content_type == "application/pdf"


def test_from_bytes_rejects_an_unsupported_extension() -> None:
    with pytest.raises(UnsupportedFormatError):
        UploadedFileMetadata.from_bytes("cv.txt", "text/plain", b"plain text")


def test_from_bytes_rejects_an_empty_file() -> None:
    with pytest.raises(EmptyContentError):
        UploadedFileMetadata.from_bytes("cv.pdf", "application/pdf", b"")


def test_from_bytes_rejects_a_file_over_the_limit() -> None:
    oversized = b"0" * (upload_rules.MAX_UPLOAD_SIZE_BYTES + 1)

    with pytest.raises(FileTooLargeError):
        UploadedFileMetadata.from_bytes("cv.pdf", "application/pdf", oversized)


@pytest.mark.parametrize(
    "sha256",
    ["not-a-digest", "", hashlib.sha256(_CONTENT).hexdigest()[:-1], "z" * 64],
)
def test_rejects_a_malformed_sha256(sha256: str) -> None:
    with pytest.raises(InvalidUploadError):
        _metadata(sha256=sha256)


def test_rejects_an_unsupported_extension_on_construction() -> None:
    with pytest.raises(UnsupportedFormatError):
        _metadata(filename="cv.exe")


def test_is_immutable() -> None:
    metadata = _metadata()

    with pytest.raises(dataclasses.FrozenInstanceError):
        metadata.filename = "other.pdf"


def test_job_description_metadata_derives_size_and_digest() -> None:
    metadata = UploadedFileMetadata.from_job_description_bytes(
        "job.txt",
        "text/plain",
        _JOB_SPEC_CONTENT,
    )

    assert metadata.filename == "job.txt"
    assert metadata.content_type == "text/plain"
    assert metadata.size_bytes == len(_JOB_SPEC_CONTENT)
    assert metadata.sha256 == hashlib.sha256(_JOB_SPEC_CONTENT).hexdigest()


@pytest.mark.parametrize("filename", ["job.txt", "job.TXT", "job.Txt"])
def test_job_description_metadata_accepts_txt_regardless_of_the_extension_case(
    filename: str,
) -> None:
    metadata = UploadedFileMetadata.from_job_description_bytes(
        filename,
        "text/plain",
        _JOB_SPEC_CONTENT,
    )

    assert metadata.filename == filename


@pytest.mark.parametrize("filename", ["job.pdf", "job.docx", "job.exe"])
def test_job_description_metadata_rejects_a_non_txt_extension(filename: str) -> None:
    with pytest.raises(UnsupportedFormatError) as exc_info:
        UploadedFileMetadata.from_job_description_bytes(
            filename,
            "text/plain",
            _JOB_SPEC_CONTENT,
        )

    assert "txt" in str(exc_info.value).lower()


def test_job_description_metadata_rejects_an_empty_file() -> None:
    with pytest.raises(EmptyContentError):
        UploadedFileMetadata.from_job_description_bytes("job.txt", "text/plain", b"")


def test_job_description_metadata_rejects_a_file_over_the_limit() -> None:
    oversized = b"0" * (upload_rules.MAX_UPLOAD_SIZE_BYTES + 1)

    with pytest.raises(FileTooLargeError):
        UploadedFileMetadata.from_job_description_bytes("job.txt", "text/plain", oversized)


def test_cv_metadata_rejects_the_job_description_extension() -> None:
    with pytest.raises(UnsupportedFormatError):
        UploadedFileMetadata.from_bytes("job.txt", "text/plain", _JOB_SPEC_CONTENT)


def test_the_validation_policy_does_not_leak_into_equality_or_repr() -> None:
    digest = hashlib.sha256(_CONTENT).hexdigest()
    permissive = frozenset({".pdf", ".txt"})
    default_policy = UploadedFileMetadata("cv.pdf", "application/pdf", 26, digest)
    custom_policy = UploadedFileMetadata(
        "cv.pdf",
        "application/pdf",
        26,
        digest,
        permissive,
    )

    assert default_policy == custom_policy
    assert "allowed_extensions" not in repr(custom_policy)
    assert UploadedFileMetadata.__slots__ == (
        "filename",
        "content_type",
        "size_bytes",
        "sha256",
    )