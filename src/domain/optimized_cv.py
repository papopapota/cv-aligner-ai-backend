from dataclasses import dataclass, field

from src.domain.audit_rules import (
    DEFAULT_R_TOTAL_TARGET,
    MAX_VARIANCE_THRESHOLD,
)
from src.domain.errors import InvalidUploadError

_MIN_VARIANCE_SCORE = 0.0
_MAX_VARIANCE_SCORE = 1.0


@dataclass(frozen=True, slots=True)
class OptimizedCV:
    content: str
    variance_score: float
    writer_attempts: int
    r_total: float | None = None
    per_dimension: dict[str, float] = field(default_factory=dict)
    gap_report: str = ""

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise InvalidUploadError("The optimized CV content is empty.")
        if not _MIN_VARIANCE_SCORE <= self.variance_score <= _MAX_VARIANCE_SCORE:
            raise InvalidUploadError(
                "The variance score must be between 0 and 1."
            )
        if self.r_total is not None and not (
            _MIN_VARIANCE_SCORE <= self.r_total <= _MAX_VARIANCE_SCORE
        ):
            raise InvalidUploadError("The R_total must be between 0 and 1.")
        if any(
            not _MIN_VARIANCE_SCORE <= score <= _MAX_VARIANCE_SCORE
            for score in self.per_dimension.values()
        ):
            raise InvalidUploadError(
                "Each dimension score must be between 0 and 1."
            )
        if self.writer_attempts < 1:
            raise InvalidUploadError(
                "The writer must run at least once."
            )

    def is_within_threshold(self) -> bool:
        variance_passed = self.variance_score <= MAX_VARIANCE_THRESHOLD
        r_total_passed = (
            self.r_total is None
            or self.r_total >= DEFAULT_R_TOTAL_TARGET
        )
        return variance_passed and r_total_passed
