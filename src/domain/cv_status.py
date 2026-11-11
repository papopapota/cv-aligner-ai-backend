from enum import StrEnum


class CVStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PARSING = "PARSING"
    PARSED = "PARSED"
    ERROR = "ERROR"


def is_ready_for_optimization(status: CVStatus) -> bool:
    return status is CVStatus.PARSED


def is_processing(status: CVStatus) -> bool:
    return status in (CVStatus.UPLOADED, CVStatus.PARSING)
