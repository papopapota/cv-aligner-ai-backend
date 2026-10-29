import dataclasses

import pytest

from src.domain.audit_rules import MAX_VARIANCE_THRESHOLD
from src.domain.errors import InvalidUploadError
from src.domain.optimized_cv import OptimizedCV

_CONTENT = "Optimized CV body"


def _optimized_cv(
    content: str = _CONTENT,
    original_variance_score: float = 0.8,
    optimized_variance_score: float = 0.1,
    writer_attempts: int = 1,
    variance_threshold: float = MAX_VARIANCE_THRESHOLD,
) -> OptimizedCV:
    return OptimizedCV(
        content=content,
        original_variance_score=original_variance_score,
        optimized_variance_score=optimized_variance_score,
        writer_attempts=writer_attempts,
        variance_threshold=variance_threshold,
    )


def test_creates_an_optimized_cv() -> None:
    optimized = _optimized_cv()

    assert optimized.content == _CONTENT
    assert optimized.original_variance_score == 0.8
    assert optimized.optimized_variance_score == 0.1
    assert optimized.writer_attempts == 1


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


def test_the_original_score_does_not_affect_the_threshold() -> None:
    assert _optimized_cv(
        original_variance_score=0.9,
        optimized_variance_score=0.1,
    ).is_within_threshold()


def test_is_immutable() -> None:
    optimized = _optimized_cv()

    with pytest.raises(dataclasses.FrozenInstanceError):
        optimized.content = "another draft"  # type: ignore[misc]
