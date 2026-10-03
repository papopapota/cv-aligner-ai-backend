from pathlib import Path

import pytest

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_SAMPLE_CV_PDF = _FIXTURES_DIR / "cv_sample.pdf"
_SAMPLE_CV_EXPECTED_TEXT = _FIXTURES_DIR / "cv_sample.expected.txt"


@pytest.fixture(scope="session")
def sample_cv_pdf() -> bytes:
    return _SAMPLE_CV_PDF.read_bytes()


@pytest.fixture(scope="session")
def sample_cv_expected_text() -> str:
    return _SAMPLE_CV_EXPECTED_TEXT.read_text(encoding="utf-8")