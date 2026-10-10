import dataclasses

import pytest

from src.domain.audit_rules import (
    DEFAULT_R_TOTAL_TARGET,
    MAX_VARIANCE_THRESHOLD,
)
from src.domain.errors import InvalidUploadError
from src.domain.optimized_cv import OptimizedCV

_CONTENT = "Optimized CV body"


def _optimized_cv(
    content: str = _CONTENT,
    variance_score: float = 0.1,
    writer_attempts: int = 1,
    r_total: float | None = None,
    per_dimension: dict[str, float] | None = None,
    gap_report: str = "",
) -> OptimizedCV:
    return OptimizedCV(
        content=content,
        variance_score=variance_score,
        writer_attempts=writer_attempts,
        r_total=r_total,
        per_dimension=per_dimension if per_dimension is not None else {},
        gap_report=gap_report,
    )


def test_creates_an_optimized_cv() -> None:
    optimized = _optimized_cv()

    assert optimized.content == _CONTENT
    assert optimized.variance_score == 0.1
    assert optimized.writer_attempts == 1
    assert optimized.r_total is None
    assert optimized.per_dimension == {}
    assert optimized.gap_report == ""


def test_keeps_the_score_breakdown() -> None:
    optimized = _optimized_cv(
        r_total=0.82,
        per_dimension={"technical_skills": 0.9, "experience": 0.7},
        gap_report="Faltan certificaciones.",
    )

    assert optimized.r_total == 0.82
    assert optimized.per_dimension == {
        "technical_skills": 0.9,
        "experience": 0.7,
    }
    assert optimized.gap_report == "Faltan certificaciones."


@pytest.mark.parametrize("r_total", [-0.1, 1.1])
def test_rejects_an_r_total_outside_the_unit_range(r_total: float) -> None:
    with pytest.raises(InvalidUploadError):
        _optimized_cv(r_total=r_total)


@pytest.mark.parametrize("score", [-0.1, 1.1])
def test_rejects_a_dimension_score_outside_the_unit_range(score: float) -> None:
    with pytest.raises(InvalidUploadError):
        _optimized_cv(per_dimension={"technical_skills": score})


@pytest.mark.parametrize("content", ["", "   ", "\n\t"])
def test_rejects_blank_content(content: str) -> None:
    with pytest.raises(InvalidUploadError):
        _optimized_cv(content=content)


@pytest.mark.parametrize("score", [-0.1, 1.1])
def test_rejects_a_score_outside_the_unit_range(score: float) -> None:
    with pytest.raises(InvalidUploadError):
        _optimized_cv(variance_score=score)


@pytest.mark.parametrize("attempts", [0, -1])
def test_rejects_a_writer_that_never_ran(attempts: int) -> None:
    with pytest.raises(InvalidUploadError):
        _optimized_cv(writer_attempts=attempts)


def test_is_within_the_threshold() -> None:
    assert _optimized_cv(variance_score=MAX_VARIANCE_THRESHOLD).is_within_threshold()
    assert not _optimized_cv(
        variance_score=MAX_VARIANCE_THRESHOLD + 0.01
    ).is_within_threshold()


def test_is_within_the_threshold_requires_the_dual_gate() -> None:
    assert _optimized_cv(
        variance_score=MAX_VARIANCE_THRESHOLD,
        r_total=DEFAULT_R_TOTAL_TARGET,
    ).is_within_threshold()
    assert not _optimized_cv(
        variance_score=MAX_VARIANCE_THRESHOLD,
        r_total=DEFAULT_R_TOTAL_TARGET - 0.01,
    ).is_within_threshold()


def test_is_immutable() -> None:
    optimized = _optimized_cv()

    with pytest.raises(dataclasses.FrozenInstanceError):
        optimized.content = "another draft"  # type: ignore[misc]
