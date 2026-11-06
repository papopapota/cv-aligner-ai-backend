import dataclasses

import pytest

from src.domain.semantic_profile import SemanticProfile


def test_as_dimensions_only_includes_non_empty_fields() -> None:
    profile = SemanticProfile(
        summary="Engineer",
        technical_skills="python",
        experience="",
        education="CS degree",
        certifications="",
        languages="english",
    )

    assert profile.as_dimensions() == {
        "technical_skills": "python",
        "education": "CS degree",
        "languages": "english",
    }


def test_as_dimensions_is_empty_when_there_are_no_values() -> None:
    assert SemanticProfile().as_dimensions() == {}


def test_is_immutable() -> None:
    profile = SemanticProfile()

    with pytest.raises(dataclasses.FrozenInstanceError):
        profile.technical_skills = "python"  # type: ignore[misc]