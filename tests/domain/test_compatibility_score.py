import dataclasses

import pytest

from src.domain.compatibility_score import CompatibilityScore
from src.domain.errors import InvalidUploadError


def _score(
    ncos: float = 0.8,
    ntfidf: float = 0.7,
    neuc: float = 0.6,
    ic: float = 75.0,
    per_dimension: dict[str, float] | None = None,
) -> CompatibilityScore:
    return CompatibilityScore(
        ncos=ncos,
        ntfidf=ntfidf,
        neuc=neuc,
        ic=ic,
        per_dimension=per_dimension or {},
    )


def test_builds_a_compatibility_score() -> None:
    score = _score(
        per_dimension={"technical_skills": 0.9, "experience": 0.6},
    )

    assert score.ncos == 0.8
    assert score.ntfidf == 0.7
    assert score.neuc == 0.6
    assert score.ic == 75.0
    assert score.per_dimension == {"technical_skills": 0.9, "experience": 0.6}


def test_per_dimension_defaults_to_empty() -> None:
    assert _score().per_dimension == {}


@pytest.mark.parametrize(
    ("ncos", "ntfidf", "neuc", "ic", "name"),
    [
        (-0.1, 0.5, 0.5, 50.0, "ncos"),
        (1.1, 0.5, 0.5, 50.0, "ncos"),
        (0.5, -0.1, 0.5, 50.0, "ntfidf"),
        (0.5, 1.1, 0.5, 50.0, "ntfidf"),
        (0.5, 0.5, -0.1, 50.0, "neuc"),
        (0.5, 0.5, 1.1, 50.0, "neuc"),
        (0.5, 0.5, 0.5, -0.1, "ic"),
        (0.5, 0.5, 0.5, 100.1, "ic"),
    ],
)
def test_rejects_a_metric_outside_its_range(
    ncos: float,
    ntfidf: float,
    neuc: float,
    ic: float,
    name: str,
) -> None:
    with pytest.raises(InvalidUploadError):
        _score(ncos=ncos, ntfidf=ntfidf, neuc=neuc, ic=ic)


@pytest.mark.parametrize("score", [-0.2, 1.2])
def test_rejects_a_dimension_outside_the_unit_range(score: float) -> None:
    with pytest.raises(InvalidUploadError):
        _score(per_dimension={"experience": score})


def test_is_immutable() -> None:
    score = _score()

    with pytest.raises(dataclasses.FrozenInstanceError):
        score.ic = 90.0  # type: ignore[misc]
