import pytest

from src.domain.audit_rules import (
    MAX_VARIANCE_THRESHOLD,
    MAX_WRITER_ATTEMPTS,
    AuditDecision,
    evaluate_variance,
)
from src.domain.errors import InvalidUploadError


@pytest.mark.parametrize("score", [0.0, 0.1, MAX_VARIANCE_THRESHOLD])
def test_approves_a_score_within_the_threshold(score: float) -> None:
    assert evaluate_variance(score) is AuditDecision.APPROVED


@pytest.mark.parametrize("score", [0.36, 0.5, 1.0])
def test_retries_a_score_above_the_threshold(score: float) -> None:
    assert evaluate_variance(score) is AuditDecision.RETRY


@pytest.mark.parametrize("score", [-0.1, 1.1, 42.0])
def test_rejects_a_score_outside_the_unit_range(score: float) -> None:
    with pytest.raises(InvalidUploadError):
        evaluate_variance(score)


def test_the_threshold_is_a_valid_score() -> None:
    assert 0.0 <= MAX_VARIANCE_THRESHOLD <= 1.0


def test_the_writer_attempt_cap_is_positive() -> None:
    assert MAX_WRITER_ATTEMPTS >= 1
