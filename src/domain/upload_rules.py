from pathlib import Path

from src.domain.errors import (
    EmptyContentError,
    FileTooLargeError,
    UnsupportedFormatError,
)

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = frozenset({".pdf", ".docx"})
JOB_DESCRIPTION_ALLOWED_EXTENSIONS = frozenset({".txt"})
_MEGABYTE = 1024 * 1024


def ensure_size_within_limit(size_bytes: int) -> None:
    if size_bytes <= 0:
        raise EmptyContentError("The uploaded file is empty.")
    if size_bytes > MAX_UPLOAD_SIZE_BYTES:
        limit_in_mb = MAX_UPLOAD_SIZE_BYTES // _MEGABYTE
        raise FileTooLargeError(
            f"The uploaded file exceeds the maximum size of {limit_in_mb} MB."
        )


def ensure_allowed_extension(
    filename: str,
    allowed_extensions: frozenset[str] | None = None,
) -> None:
    extensions = allowed_extensions or ALLOWED_EXTENSIONS
    if Path(filename).suffix.lower() not in extensions:
        allowed = ", ".join(sorted(extensions))
        raise UnsupportedFormatError(
            f"Unsupported file format. Allowed extensions: {allowed}."
        )


def ensure_job_description_extension(filename: str) -> None:
    ensure_allowed_extension(filename, JOB_DESCRIPTION_ALLOWED_EXTENSIONS)


def ensure_non_empty_text(text: str) -> None:
    if not text.strip():
        raise EmptyContentError("The extracted text is empty.")