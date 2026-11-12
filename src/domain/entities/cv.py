from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.cv_status import CVStatus, is_ready_for_optimization
from src.domain.errors import InvalidUploadError
from src.domain.structured_cv import StructuredCV


@dataclass(frozen=True, slots=True)
class CV:
    id: UUID
    user_id: int
    s3_key: str
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    status: CVStatus
    raw_text: str | None = None
    structured_cv: StructuredCV | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.s3_key.strip():
            raise InvalidUploadError("The CV s3_key cannot be empty.")
        if not self.filename.strip():
            raise InvalidUploadError("The CV filename cannot be empty.")
        if self.size_bytes <= 0:
            raise InvalidUploadError("The CV size must be greater than zero.")
        if self.status is CVStatus.ERROR and not (
            self.error_code and self.error_message
        ):
            raise InvalidUploadError(
                "A CV in ERROR status must include an error code and message."
            )

    def is_ready_for_optimization(self) -> bool:
        return is_ready_for_optimization(self.status)

    def is_failed(self) -> bool:
        return self.status is CVStatus.ERROR
