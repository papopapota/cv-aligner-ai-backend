import pytest

from src.domain import upload_rules
from src.domain.errors import (
    EmptyContentError,
    FileTooLargeError,
    UnsupportedFormatError,
)


def test_ensure_size_within_limit_accepts_the_maximum() -> None:
    upload_rules.ensure_size_within_limit(upload_rules.MAX_UPLOAD_SIZE_BYTES)


def test_ensure_size_within_limit_rejects_a_size_over_the_maximum() -> None:
    oversized = upload_rules.MAX_UPLOAD_SIZE_BYTES + 1

    with pytest.raises(FileTooLargeError):
        upload_rules.ensure_size_within_limit(oversized)


def test_ensure_size_within_limit_rejects_zero_bytes() -> None:
    with pytest.raises(EmptyContentError):
        upload_rules.ensure_size_within_limit(0)


@pytest.mark.parametrize(
    "filename",
    ["cv.pdf", "cv.docx", "CV.PDF", "cv.DocX", "path/to/my cv.pdf"],
)
def test_ensure_allowed_extension_accepts_supported_formats(filename: str) -> None:
    upload_rules.ensure_allowed_extension(filename)


@pytest.mark.parametrize(
    "filename",
    ["cv.txt", "cv.exe", "cv", "cv.pdf.exe", "cvpdf"],
)
def test_ensure_allowed_extension_rejects_unsupported_formats(filename: str) -> None:
    with pytest.raises(UnsupportedFormatError):
        upload_rules.ensure_allowed_extension(filename)


def test_ensure_non_empty_text_accepts_real_text() -> None:
    upload_rules.ensure_non_empty_text("Python developer with 5 years of experience.")


@pytest.mark.parametrize("text", ["", "   ", "\n\t "])
def test_ensure_non_empty_text_rejects_blank_text(text: str) -> None:
    with pytest.raises(EmptyContentError):
        upload_rules.ensure_non_empty_text(text)