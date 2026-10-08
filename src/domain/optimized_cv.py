from dataclasses import dataclass

from src.domain.audit_rules import MAX_VARIANCE_THRESHOLD
from src.domain.errors import InvalidUploadError

_MIN_VARIANCE_SCORE = 0.0
_MAX_VARIANCE_SCORE = 1.0


@dataclass(frozen=True, slots=True)
class OptimizedCV:
    content: str
    variance_score: float
    writer_attempts: int

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise InvalidUploadError("The optimized CV content is empty.")
        if not _MIN_VARIANCE_SCORE <= self.variance_score <= _MAX_VARIANCE_SCORE:
            raise InvalidUploadError(
                "The variance score must be between 0 and 1."
            )
        if self.writer_attempts < 1:
            raise InvalidUploadError(
                "The writer must run at least once."
            )

    def is_within_threshold(self) -> bool:
        return self.variance_score <= MAX_VARIANCE_THRESHOLD
