import dataclasses

import pytest

from src.domain.errors import InvalidStructureError
from src.domain.semantic_profile import SemanticProfile


def test_as_dimensions_only_includes_non_empty_fields() -> None:
    profile = SemanticProfile(
        summary="Engineer",
        technical_skills="python",
        experience="",
        projects="api platform",
        education="CS degree",
        certifications="",
        languages="english",
    )

    assert profile.as_dimensions() == {
        "technical_skills": "python",
        "projects": "api platform",
        "education": "CS degree",
        "languages": "english",
    }


def test_as_dimensions_is_empty_when_there_are_no_values() -> None:
    assert SemanticProfile().as_dimensions() == {}


def test_to_dict_round_trips_through_from_mapping() -> None:
    profile = SemanticProfile(
        summary="Engineer",
        technical_skills="python",
        experience="5 years",
        projects="api",
        education="CS",
        certifications="AWS",
        languages="english",
    )

    assert SemanticProfile.from_mapping(profile.to_dict()) == profile


def test_from_mapping_joins_lists() -> None:
    profile = SemanticProfile.from_mapping(
        {"summary": "Engineer", "technical_skills": ["python", "go"]}
    )

    assert profile.technical_skills == "python; go"


def test_from_mapping_ignores_non_mapping_payloads() -> None:
    assert SemanticProfile.from_mapping("not a mapping") == SemanticProfile()


def test_from_json_text_parses_a_fenced_object() -> None:
    profile = SemanticProfile.from_json_text(
        '```json\n{"summary": "Engineer", "technical_skills": "python"}\n```'
    )

    assert profile.summary == "Engineer"
    assert profile.technical_skills == "python"


def test_from_json_text_rejects_invalid_content() -> None:
    with pytest.raises(InvalidStructureError):
        SemanticProfile.from_json_text("I cannot extract a profile")


def test_to_text_includes_only_non_empty_sections() -> None:
    profile = SemanticProfile(
        summary="Engineer",
        technical_skills="python",
        experience="5 years",
        projects="api",
        education="CS",
        certifications="AWS",
        languages="english",
    )

    assert profile.to_text() == (
        "Summary: Engineer\n"
        "Technical skills: python\n"
        "Experience: 5 years\n"
        "Projects: api\n"
        "Education: CS\n"
        "Certifications: AWS\n"
        "Languages: english"
    )


def test_to_text_is_empty_for_an_empty_profile() -> None:
    assert SemanticProfile().to_text() == ""


def test_is_empty() -> None:
    assert SemanticProfile().is_empty()
    assert not SemanticProfile(summary="Engineer").is_empty()
    assert not SemanticProfile(projects="api").is_empty()


def test_is_immutable() -> None:
    profile = SemanticProfile()

    with pytest.raises(dataclasses.FrozenInstanceError):
        profile.technical_skills = "python"  # type: ignore[misc]
