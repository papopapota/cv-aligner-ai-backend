from collections.abc import Sequence
from dataclasses import dataclass
from math import fsum, sqrt

_MIN_NORMALIZED = 0.0
_MAX_NORMALIZED = 1.0
_MIN_IC = 0.0
_MAX_IC = 100.0
_PROBABILITY_TOLERANCE = 1e-9


@dataclass(frozen=True, slots=True)
class CompatibilityWeights:
    ncos: float = 0.50
    ntfidf: float = 0.30
    neuc: float = 0.20

    def __post_init__(self) -> None:
        for name, value in (
            ("ncos", self.ncos),
            ("ntfidf", self.ntfidf),
            ("neuc", self.neuc),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"The '{name}' weight must be between 0 and 1.")
        total = self.ncos + self.ntfidf + self.neuc
        if abs(total - 1.0) > _PROBABILITY_TOLERANCE:
            raise ValueError(
                "Compatibility weights must sum to 1 "
                f"(got {total:.6f})."
            )


DEFAULT_COMPATIBILITY_WEIGHTS = CompatibilityWeights()


def normalized_cosine(
    resume_vector: Sequence[float],
    job_vector: Sequence[float],
) -> float:
    _ensure_same_dimension(resume_vector, job_vector)
    resume_norm = sqrt(fsum(value * value for value in resume_vector))
    job_norm = sqrt(fsum(value * value for value in job_vector))
    if resume_norm == 0.0 or job_norm == 0.0:
        return 0.0
    dot = fsum(left * right for left, right in zip(resume_vector, job_vector))
    return _clamp_normalized(dot / (resume_norm * job_norm))


def normalized_euclidean(
    resume_vector: Sequence[float],
    job_vector: Sequence[float],
    dmax: float = 2.0,
) -> float:
    _ensure_same_dimension(resume_vector, job_vector)
    if dmax <= 0.0:
        raise ValueError("dmax must be greater than zero.")
    resume_unit = _unit_vector(resume_vector)
    job_unit = _unit_vector(job_vector)
    if resume_unit is None or job_unit is None:
        return 0.0
    distance = sqrt(
        fsum(
            (left - right) ** 2
            for left, right in zip(resume_unit, job_unit)
        )
    )
    return _clamp_normalized(1.0 - distance / dmax)


def compatibility_index(
    ncos: float,
    ntfidf: float,
    neuc: float,
    weights: CompatibilityWeights = DEFAULT_COMPATIBILITY_WEIGHTS,
) -> float:
    ic = 100.0 * (
        weights.ncos * _clamp_normalized(ncos)
        + weights.ntfidf * _clamp_normalized(ntfidf)
        + weights.neuc * _clamp_normalized(neuc)
    )
    return min(max(ic, _MIN_IC), _MAX_IC)


def _ensure_same_dimension(
    left: Sequence[float],
    right: Sequence[float],
) -> None:
    if len(left) != len(right):
        raise ValueError("Embedding vectors must have the same dimension.")


def _unit_vector(values: Sequence[float]) -> tuple[float, ...] | None:
    norm = sqrt(fsum(value * value for value in values))
    if norm == 0.0:
        return None
    return tuple(value / norm for value in values)


def _clamp_normalized(value: float) -> float:
    return min(max(value, _MIN_NORMALIZED), _MAX_NORMALIZED)
