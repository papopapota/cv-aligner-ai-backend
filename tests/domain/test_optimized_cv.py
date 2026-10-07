import dataclasses

import pytest

from src.domain.audit_rules import MAX_VARIANCE_THRESHOLD
from src.domain.errors import InvalidUploadError
from src.domain.optimized_cv import OptimizedCV

_CONTENT = "Optimized CV body"


def _optimized_cv(
    content: str = _CONTENT,
    variance_score: float = 0.1,
    writer_attempts: int = 1,
) -> OptimizedCV:
    return OptimizedCV(
        content=content,
        variance_score=variance_score,
        writer_attempts=writer_attempts,
    )


def test_creates_an_optimized_cv() -> None:
    optimized = _optimized_cv()

    assert optimized.content == _CONTENT
    assert optimized.variance_score == 0.1
    assert optimized.writer_attempts == 1


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


def test_is_immutable() -> None:
    optimized = _optimized_cv()

    with pytest.raises(dataclasses.FrozenInstanceError):
        optimized.content = "another draft"  # type: ignore[misc]
