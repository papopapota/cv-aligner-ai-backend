import pytest

from src.domain.cv_status import CVStatus, is_processing, is_ready_for_optimization


def test_status_values() -> None:
    assert CVStatus.UPLOADED == "UPLOADED"
    assert CVStatus.PARSING == "PARSING"
    assert CVStatus.PARSED == "PARSED"
    assert CVStatus.ERROR == "ERROR"


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (CVStatus.UPLOADED, False),
        (CVStatus.PARSING, False),
        (CVStatus.PARSED, True),
        (CVStatus.ERROR, False),
    ],
)
def test_is_ready_for_optimization(status: CVStatus, expected: bool) -> None:
    assert is_ready_for_optimization(status) is expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (CVStatus.UPLOADED, True),
        (CVStatus.PARSING, True),
        (CVStatus.PARSED, False),
        (CVStatus.ERROR, False),
    ],
)
def test_is_processing(status: CVStatus, expected: bool) -> None:
    assert is_processing(status) is expected
