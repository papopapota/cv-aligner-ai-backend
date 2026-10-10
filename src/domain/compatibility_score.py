from dataclasses import dataclass, field

from src.domain.errors import InvalidUploadError

_MIN_SCORE = 0.0
_MAX_SCORE = 1.0
_TOLERANCE = 1e-9

_METRIC_NAMES = ("s_cosine", "d_euclidean", "a_contextual", "r_total")


@dataclass(frozen=True, slots=True)
class CompatibilityScore:
    s_cosine: float
    d_euclidean: float
    a_contextual: float
    r_total: float
    per_dimension: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, value in zip(
            _METRIC_NAMES,
            (self.s_cosine, self.d_euclidean, self.a_contextual, self.r_total),
            strict=True,
        ):
            if not _MIN_SCORE <= value <= _MAX_SCORE + _TOLERANCE:
                raise InvalidUploadError(
                    f"The {name} score must be between 0 and 1."
                )
        for dimension, score in self.per_dimension.items():
            if not _MIN_SCORE <= score <= _MAX_SCORE + _TOLERANCE:
                raise InvalidUploadError(
                    f"The '{dimension}' score must be between 0 and 1."
                )