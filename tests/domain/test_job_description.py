import dataclasses

import pytest

from src.domain.errors import EmptyContentError
from src.domain.job_description import JobDescription

_RAW_TEXT = "We are looking for a Python developer with FastAPI experience."


def test_create_job_description() -> None:
    description = JobDescription(raw_text=_RAW_TEXT)

    assert description.raw_text == _RAW_TEXT


@pytest.mark.parametrize("raw_text", ["", "   ", "\n\t "])
def test_rejects_blank_raw_text(raw_text: str) -> None:
    with pytest.raises(EmptyContentError):
        JobDescription(raw_text=raw_text)


def test_is_immutable() -> None:
    description = JobDescription(raw_text=_RAW_TEXT)

    with pytest.raises(dataclasses.FrozenInstanceError):
        description.raw_text = "another offer"