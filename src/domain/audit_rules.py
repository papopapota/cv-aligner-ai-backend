from enum import Enum

from src.domain.errors import InvalidUploadError

MAX_VARIANCE_THRESHOLD = 0.35
MAX_WRITER_ATTEMPTS = 3


class AuditDecision(Enum):
    RETRY = "retry"
    APPROVED = "approved"


def evaluate_variance(variance_score: float) -> AuditDecision:
    if not 0.0 <= variance_score <= 1.0:
        raise InvalidUploadError(
            "The variance score must be between 0 and 1."
        )
    if variance_score <= MAX_VARIANCE_THRESHOLD:
        return AuditDecision.APPROVED
    return AuditDecision.RETRY
