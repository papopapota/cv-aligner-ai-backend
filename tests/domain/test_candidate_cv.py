import hashlib

import pytest

from src.domain.candidate_cv import CandidateCV
from src.domain.errors import EmptyContentError
from src.domain.semantic_profile import SemanticProfile
from src.domain.uploaded_file_metadata import UploadedFileMetadata

_RAW_TEXT = "Python developer with 5 years of experience in FastAPI."


def _metadata() -> UploadedFileMetadata:
    content = b"%PDF-1.7 fake resume bytes"
    return UploadedFileMetadata(
        filename="cv.pdf",
        content_type="application/pdf",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )


def test_create_candidate_cv() -> None:
    metadata = _metadata()

    candidate = CandidateCV(metadata=metadata, raw_text=_RAW_TEXT)

    assert candidate.metadata is metadata
    assert candidate.raw_text == _RAW_TEXT


@pytest.mark.parametrize("raw_text", ["", "   ", "\n\t "])
def test_rejects_blank_raw_text(raw_text: str) -> None:
    with pytest.raises(EmptyContentError):
        CandidateCV(metadata=_metadata(), raw_text=raw_text)


def test_keeps_an_optional_technical_profile() -> None:
    profile = SemanticProfile(
        summary="Backend engineer",
        technical_skills="python",
    )

    candidate = CandidateCV(
        metadata=_metadata(),
        raw_text=_RAW_TEXT,
        technical_profile=profile,
    )

    assert candidate.technical_profile == profile


def test_technical_profile_defaults_to_none() -> None:
    candidate = CandidateCV(metadata=_metadata(), raw_text=_RAW_TEXT)

    assert candidate.technical_profile is None
