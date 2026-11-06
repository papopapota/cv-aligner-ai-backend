import dataclasses

import pytest

from src.domain.audit_rules import (
    DEFAULT_IC_TARGET,
    MAX_VARIANCE_THRESHOLD,
)
from src.domain.errors import InvalidUploadError
from src.domain.optimized_cv import OptimizedCV

_CONTENT = "Optimized CV body"


def _optimized_cv(
    content: str = _CONTENT,
    original_variance_score: float = 0.8,
    optimized_variance_score: float = 0.1,
    writer_attempts: int = 1,
    variance_threshold: float = MAX_VARIANCE_THRESHOLD,
    original_ic: float | None = None,
    optimized_ic: float | None = None,
    original_per_dimension: dict[str, float] | None = None,
    optimized_per_dimension: dict[str, float] | None = None,
    gap_report: str = "",
) -> OptimizedCV:
    return OptimizedCV(
        content=content,
        original_variance_score=original_variance_score,
        optimized_variance_score=optimized_variance_score,
        writer_attempts=writer_attempts,
        variance_threshold=variance_threshold,
        original_ic=original_ic,
        optimized_ic=optimized_ic,
        original_per_dimension=(
            original_per_dimension
            if original_per_dimension is not None
            else {}
        ),
        optimized_per_dimension=(
            optimized_per_dimension
            if optimized_per_dimension is not None
            else {}
        ),
        gap_report=gap_report,
    )


def test_creates_an_optimized_cv() -> None:
    optimized = _optimized_cv()

    assert optimized.content == _CONTENT
    assert optimized.original_variance_score == 0.8
    assert optimized.optimized_variance_score == 0.1
    assert optimized.writer_attempts == 1
    assert optimized.original_ic is None
    assert optimized.optimized_ic is None
    assert optimized.original_per_dimension == {}
    assert optimized.optimized_per_dimension == {}
    assert optimized.gap_report == ""


def test_keeps_the_score_breakdown() -> None:
    optimized = _optimized_cv(
        original_ic=61.0,
        optimized_ic=82.0,
        original_per_dimension={"technical_skills": 0.5, "experience": 0.6},
        optimized_per_dimension={"technical_skills": 0.9, "experience": 0.7},
        gap_report="Faltan certificaciones.",
    )

    assert optimized.original_ic == 61.0
    assert optimized.optimized_ic == 82.0
    assert optimized.original_per_dimension == {
        "technical_skills": 0.5,
        "experience": 0.6,
    }
    assert optimized.optimized_per_dimension == {
        "technical_skills": 0.9,
        "experience": 0.7,
    }
    assert optimized.gap_report == "Faltan certificaciones."


@pytest.mark.parametrize(
    ("field", "ic"),
    [
        ("original_ic", -0.1),
        ("original_ic", 100.1),
        ("optimized_ic", -0.1),
        ("optimized_ic", 100.1),
    ],
)
def test_rejects_an_ic_outside_the_range(field: str, ic: float) -> None:
    with pytest.raises(InvalidUploadError):
        _optimized_cv(**{field: ic})


@pytest.mark.parametrize(
    ("field", "score"),
    [
        ("original_per_dimension", -0.1),
        ("original_per_dimension", 1.1),
        ("optimized_per_dimension", -0.1),
        ("optimized_per_dimension", 1.1),
    ],
)
def test_rejects_a_dimension_score_outside_the_unit_range(
    field: str,
    score: float,
) -> None:
    with pytest.raises(InvalidUploadError):
        _optimized_cv(**{field: {"technical_skills": score}})


@pytest.mark.parametrize("content", ["", "   ", "\n\t"])
def test_rejects_blank_content(content: str) -> None:
    with pytest.raises(InvalidUploadError):
        _optimized_cv(content=content)


@pytest.mark.parametrize("score", [-0.1, 1.1])
def test_rejects_an_original_score_outside_the_unit_range(score: float) -> None:
    with pytest.raises(InvalidUploadError):
        _optimized_cv(original_variance_score=score)


@pytest.mark.parametrize("score", [-0.1, 1.1])
def test_rejects_an_optimized_score_outside_the_unit_range(score: float) -> None:
    with pytest.raises(InvalidUploadError):
        _optimized_cv(optimized_variance_score=score)


@pytest.mark.parametrize("attempts", [0, -1])
def test_rejects_a_writer_that_never_ran(attempts: int) -> None:
    with pytest.raises(InvalidUploadError):
        _optimized_cv(writer_attempts=attempts)


def test_is_within_the_threshold() -> None:
    assert _optimized_cv(
        optimized_variance_score=MAX_VARIANCE_THRESHOLD
    ).is_within_threshold()
    assert not _optimized_cv(
        optimized_variance_score=MAX_VARIANCE_THRESHOLD + 0.01
    ).is_within_threshold()


def test_uses_a_custom_threshold() -> None:
    assert _optimized_cv(
        optimized_variance_score=0.6,
        variance_threshold=0.7,
    ).is_within_threshold()
    assert not _optimized_cv(
        optimized_variance_score=0.6,
        variance_threshold=0.5,
    ).is_within_threshold()


def test_is_within_the_threshold_requires_the_dual_gate() -> None:
    assert _optimized_cv(
        optimized_variance_score=MAX_VARIANCE_THRESHOLD,
        optimized_ic=DEFAULT_IC_TARGET,
    ).is_within_threshold()
    assert not _optimized_cv(
        optimized_variance_score=MAX_VARIANCE_THRESHOLD,
        optimized_ic=DEFAULT_IC_TARGET - 1.0,
    ).is_within_threshold()


def test_the_original_ic_does_not_affect_the_threshold() -> None:
    assert _optimized_cv(
        original_ic=DEFAULT_IC_TARGET - 1.0,
        optimized_ic=DEFAULT_IC_TARGET,
    ).is_within_threshold()
    assert not _optimized_cv(
        original_ic=DEFAULT_IC_TARGET,
        optimized_ic=DEFAULT_IC_TARGET - 1.0,
    ).is_within_threshold()


def test_the_original_variance_does_not_affect_the_threshold() -> None:
    assert _optimized_cv(
        original_variance_score=0.9,
        optimized_variance_score=0.1,
    ).is_within_threshold()


def test_is_immutable() -> None:
    optimized = _optimized_cv()

    with pytest.raises(dataclasses.FrozenInstanceError):
        optimized.content = "another draft"  # type: ignore[misc]
