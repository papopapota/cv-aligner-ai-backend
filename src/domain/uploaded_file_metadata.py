import hashlib
from dataclasses import dataclass

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

    def __post_init__(self) -> None:
        upload_rules.ensure_allowed_extension(self.filename)
        upload_rules.ensure_size_within_limit(self.size_bytes)
        self._ensure_valid_sha256()

    @classmethod
    def from_bytes(
        cls,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> "UploadedFileMetadata":
        return cls(
            filename=filename,
            content_type=content_type,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )

    @classmethod
    def from_job_description_bytes(
        cls,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> "UploadedFileMetadata":
        # Bypass __post_init__ validation by using object.__new__ and object.__setattr__
        instance = object.__new__(cls)
        object.__setattr__(instance, "filename", filename)
        object.__setattr__(instance, "content_type", content_type)
        object.__setattr__(instance, "size_bytes", len(content))
        object.__setattr__(instance, "sha256", hashlib.sha256(content).hexdigest())
        # Validate with job description rules
        upload_rules.ensure_job_description_extension(filename)
        upload_rules.ensure_size_within_limit(len(content))
        return instance

    def _ensure_valid_sha256(self) -> None:
        digest = self.sha256.lower()
        if len(digest) != _SHA256_LENGTH or not set(digest) <= _HEX_DIGITS:
            raise InvalidUploadError(
                "sha256 must be a 64-character hexadecimal digest."
            )