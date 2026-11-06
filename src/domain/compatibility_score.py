from dataclasses import dataclass, field

from src.domain.errors import InvalidUploadError

_MIN_NORMALIZED = 0.0
_MAX_NORMALIZED = 1.0
_MIN_IC = 0.0
_MAX_IC = 100.0
_TOLERANCE = 1e-9

_NORMALIZED_METRIC_NAMES = ("ncos", "ntfidf", "neuc")


@dataclass(frozen=True, slots=True)
class CompatibilityScore:
    ncos: float
    ntfidf: float
    neuc: float
    ic: float
    per_dimension: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, value in zip(
            _NORMALIZED_METRIC_NAMES,
            (self.ncos, self.ntfidf, self.neuc),
            strict=True,
        ):
            if not _MIN_NORMALIZED <= value <= _MAX_NORMALIZED + _TOLERANCE:
                raise InvalidUploadError(
                    f"The {name} metric must be between 0 and 1."
                )
        if not _MIN_IC <= self.ic <= _MAX_IC + _TOLERANCE:
            raise InvalidUploadError("The IC must be between 0 and 100.")
        for dimension, score in self.per_dimension.items():
            if not _MIN_NORMALIZED <= score <= _MAX_NORMALIZED + _TOLERANCE:
                raise InvalidUploadError(
                    f"The '{dimension}' score must be between 0 and 1."
                )
