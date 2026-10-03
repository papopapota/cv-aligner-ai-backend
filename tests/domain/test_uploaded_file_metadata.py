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