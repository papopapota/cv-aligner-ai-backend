import dataclasses
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.domain.cv_status import CVStatus
from src.domain.entities.cv import CV
from src.domain.errors import InvalidUploadError
from src.domain.personal_info import PersonalInfo
from src.domain.semantic_profile import SemanticProfile
from src.domain.structured_cv import StructuredCV


def _cv(**overrides: object) -> CV:
    values: dict[str, object] = {
        "id": uuid4(),
        "user_id": 1,
        "s3_key": "users/1/cv.pdf",
        "filename": "cv.pdf",
        "content_type": "application/pdf",
        "size_bytes": 10,
        "sha256": "a" * 64,
        "status": CVStatus.UPLOADED,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return CV(**values)  # type: ignore[arg-type]


def test_creates_a_cv_with_its_metadata() -> None:
    cv = _cv()

    assert cv.user_id == 1
    assert cv.s3_key == "users/1/cv.pdf"
    assert cv.filename == "cv.pdf"
    assert cv.content_type == "application/pdf"
    assert cv.size_bytes == 10
    assert cv.sha256 == "a" * 64
    assert cv.status is CVStatus.UPLOADED
    assert cv.raw_text is None
    assert cv.structured_cv is None
    assert cv.error_code is None
    assert cv.error_message is None


def test_keeps_the_structured_cv_and_raw_text() -> None:
    structured = StructuredCV(
        personal_info=PersonalInfo(full_name="Ana"),
        technical_data=SemanticProfile(summary="Engineer"),
    )

    cv = _cv(
        status=CVStatus.PARSED,
        raw_text="Ana\nEngineer",
        structured_cv=structured,
    )

    assert cv.raw_text == "Ana\nEngineer"
    assert cv.structured_cv == structured


def test_is_ready_for_optimization_only_when_parsed() -> None:
    assert not _cv(status=CVStatus.UPLOADED).is_ready_for_optimization()
    assert not _cv(status=CVStatus.PARSING).is_ready_for_optimization()
    assert _cv(status=CVStatus.PARSED).is_ready_for_optimization()
    assert not _cv(
        status=CVStatus.ERROR,
        error_code="PARSE_FAILED",
        error_message="The CV could not be processed.",
    ).is_ready_for_optimization()


def test_is_failed_only_when_the_status_is_error() -> None:
    assert not _cv(status=CVStatus.PARSED).is_failed()
    assert _cv(
        status=CVStatus.ERROR,
        error_code="PARSE_FAILED",
        error_message="The CV could not be processed.",
    ).is_failed()


def test_error_status_requires_an_error_code_and_message() -> None:
    with pytest.raises(InvalidUploadError):
        _cv(status=CVStatus.ERROR)
    with pytest.raises(InvalidUploadError):
        _cv(status=CVStatus.ERROR, error_code="PARSE_FAILED")
    with pytest.raises(InvalidUploadError):
        _cv(status=CVStatus.ERROR, error_message="The CV could not be processed.")


@pytest.mark.parametrize(
    "overrides",
    [
        {"s3_key": ""},
        {"s3_key": "   "},
        {"filename": ""},
        {"filename": "   "},
        {"size_bytes": 0},
        {"size_bytes": -1},
    ],
)
def test_rejects_invalid_metadata(overrides: dict[str, object]) -> None:
    with pytest.raises(InvalidUploadError):
        _cv(**overrides)


def test_is_immutable() -> None:
    cv = _cv()

    with pytest.raises(dataclasses.FrozenInstanceError):
        cv.status = CVStatus.PARSED  # type: ignore[misc]
