import hashlib
from dataclasses import InitVar, dataclass

from src.domain import upload_rules
from src.domain.errors import InvalidUploadError

_SHA256_LENGTH = 64
_HEX_DIGITS = frozenset("0123456789abcdef")


@dataclass(frozen=True, slots=True)
class UploadedFileMetadata:
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    allowed_extensions: InitVar[frozenset[str]] = upload_rules.ALLOWED_EXTENSIONS

    def __post_init__(self, allowed_extensions: frozenset[str]) -> None:
        upload_rules.ensure_allowed_extension(self.filename, allowed_extensions)
        upload_rules.ensure_size_within_limit(self.size_bytes)
        self._ensure_valid_sha256()

    @classmethod
    def _build(
        cls,
        filename: str,
        content_type: str,
        content: bytes,
        allowed_extensions: frozenset[str],
    ) -> "UploadedFileMetadata":
        return cls(
            filename=filename,
            content_type=content_type,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            allowed_extensions=allowed_extensions,
        )

    @classmethod
    def from_bytes(
        cls,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> "UploadedFileMetadata":
        return cls._build(
            filename=filename,
            content_type=content_type,
            content=content,
            allowed_extensions=upload_rules.ALLOWED_EXTENSIONS,
        )

    @classmethod
    def from_job_description_bytes(
        cls,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> "UploadedFileMetadata":
        return cls._build(
            filename=filename,
            content_type=content_type,
            content=content,
            allowed_extensions=upload_rules.JOB_DESCRIPTION_ALLOWED_EXTENSIONS,
        )

    def _ensure_valid_sha256(self) -> None:
        digest = self.sha256.lower()
        if len(digest) != _SHA256_LENGTH or not set(digest) <= _HEX_DIGITS:
            raise InvalidUploadError(
                "sha256 must be a 64-character hexadecimal digest."
            )