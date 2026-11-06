from dataclasses import dataclass, field

from src.domain.audit_rules import (
    DEFAULT_IC_TARGET,
    MAX_VARIANCE_THRESHOLD,
)
from src.domain.errors import InvalidUploadError

_MIN_VARIANCE_SCORE = 0.0
_MAX_VARIANCE_SCORE = 1.0
_MIN_IC = 0.0
_MAX_IC = 100.0


@dataclass(frozen=True, slots=True)
class OptimizedCV:
    content: str
    original_variance_score: float
    optimized_variance_score: float
    writer_attempts: int
    variance_threshold: float = MAX_VARIANCE_THRESHOLD
    original_ic: float | None = None
    optimized_ic: float | None = None
    original_per_dimension: dict[str, float] = field(default_factory=dict)
    optimized_per_dimension: dict[str, float] = field(default_factory=dict)
    gap_report: str = ""

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
        for name, ic in (
            ("original", self.original_ic),
            ("optimized", self.optimized_ic),
        ):
            if ic is not None and not (_MIN_IC <= ic <= _MAX_IC):
                raise InvalidUploadError(
                    f"The {name} IC must be between 0 and 100."
                )
        for name, per_dimension in (
            ("original", self.original_per_dimension),
            ("optimized", self.optimized_per_dimension),
        ):
            if any(
                not _MIN_VARIANCE_SCORE <= score <= _MAX_VARIANCE_SCORE
                for score in per_dimension.values()
            ):
                raise InvalidUploadError(
                    f"Each {name} dimension score must be between 0 and 1."
                )
        if self.writer_attempts < 1:
            raise InvalidUploadError("The writer must run at least once.")

    def is_within_threshold(self) -> bool:
        variance_passed = (
            self.optimized_variance_score <= self.variance_threshold
        )
        ic_passed = (
            self.optimized_ic is None
            or self.optimized_ic >= DEFAULT_IC_TARGET
        )
        return variance_passed and ic_passed
