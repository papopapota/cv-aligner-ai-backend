import dataclasses

import pytest

from src.domain.compatibility_score import CompatibilityScore
from src.domain.errors import InvalidUploadError


def _score(
    s_cosine: float = 0.8,
    d_euclidean: float = 0.7,
    a_contextual: float = 0.6,
    r_total: float = 0.75,
    per_dimension: dict[str, float] | None = None,
) -> CompatibilityScore:
    return CompatibilityScore(
        s_cosine=s_cosine,
        d_euclidean=d_euclidean,
        a_contextual=a_contextual,
        r_total=r_total,
        per_dimension=per_dimension or {},
    )


def test_builds_a_compatibility_score() -> None:
    score = _score(
        per_dimension={"technical_skills": 0.9, "experience": 0.6},
    )

    assert score.s_cosine == 0.8
    assert score.d_euclidean == 0.7
    assert score.a_contextual == 0.6
    assert score.r_total == 0.75
    assert score.per_dimension == {"technical_skills": 0.9, "experience": 0.6}


def test_per_dimension_defaults_to_empty() -> None:
    assert _score().per_dimension == {}


@pytest.mark.parametrize(
    ("s_cosine", "d_euclidean", "a_contextual", "r_total", "name"),
    [
        (-0.1, 0.5, 0.5, 0.5, "s_cosine"),
        (1.1, 0.5, 0.5, 0.5, "s_cosine"),
        (0.5, -0.1, 0.5, 0.5, "d_euclidean"),
        (0.5, 1.1, 0.5, 0.5, "d_euclidean"),
        (0.5, 0.5, -0.1, 0.5, "a_contextual"),
        (0.5, 0.5, 1.1, 0.5, "a_contextual"),
        (0.5, 0.5, 0.5, -0.1, "r_total"),
        (0.5, 0.5, 0.5, 1.1, "r_total"),
    ],
)
def test_rejects_a_metric_outside_the_unit_range(
    s_cosine: float,
    d_euclidean: float,
    a_contextual: float,
    r_total: float,
    name: str,
) -> None:
    with pytest.raises(InvalidUploadError):
        _score(
            s_cosine=s_cosine,
            d_euclidean=d_euclidean,
            a_contextual=a_contextual,
            r_total=r_total,
        )


@pytest.mark.parametrize("score", [-0.2, 1.2])
def test_rejects_a_dimension_outside_the_unit_range(score: float) -> None:
    with pytest.raises(InvalidUploadError):
        _score(per_dimension={"experience": score})


def test_is_immutable() -> None:
    score = _score()

    with pytest.raises(dataclasses.FrozenInstanceError):
        score.r_total = 0.9  # type: ignore[misc]