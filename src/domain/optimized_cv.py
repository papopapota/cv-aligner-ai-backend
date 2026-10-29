from dataclasses import dataclass

from src.domain.audit_rules import MAX_VARIANCE_THRESHOLD
from src.domain.errors import InvalidUploadError

_MIN_VARIANCE_SCORE = 0.0
_MAX_VARIANCE_SCORE = 1.0


@dataclass(frozen=True, slots=True)
class OptimizedCV:
    content: str
    original_variance_score: float
    optimized_variance_score: float
    writer_attempts: int
    variance_threshold: float = MAX_VARIANCE_THRESHOLD

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise InvalidUploadError("The optimized CV content is empty.")
        original_in_range = (
            _MIN_VARIANCE_SCORE
            <= self.original_variance_score
            <= _MAX_VARIANCE_SCORE
        )
        if not original_in_range:
            raise InvalidUploadError(
                "The original variance score must be between 0 and 1."
            )
        optimized_in_range = (
            _MIN_VARIANCE_SCORE
            <= self.optimized_variance_score
            <= _MAX_VARIANCE_SCORE
        )
        if not optimized_in_range:
            raise InvalidUploadError(
                "The optimized variance score must be between 0 and 1."
            )
        if self.writer_attempts < 1:
            raise InvalidUploadError("The writer must run at least once.")

    def is_within_threshold(self) -> bool:
        return self.optimized_variance_score <= self.variance_threshold
