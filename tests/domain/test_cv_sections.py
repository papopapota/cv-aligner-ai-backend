import dataclasses

import pytest

from src.domain.cv_sections import CVSections
from src.domain.errors import InvalidStructureError
from src.domain.semantic_profile import SemanticProfile


def _sections() -> CVSections:
    return CVSections(
        summary="Backend engineer",
        technical_skills="python, fastapi",
        experience="5 years",
        projects="cv-aligner",
        education="CS degree",
        certifications="AWS",
        languages="english, spanish",
    )


def test_defaults_every_section_to_an_empty_string() -> None:
    sections = CVSections()

    assert sections.to_dict() == {
        "summary": "",
        "technical_skills": "",
        "experience": "",
        "projects": "",
        "education": "",
        "certifications": "",
        "languages": "",
    }
    assert sections.is_empty()


def test_from_mapping_parses_all_sections() -> None:
    sections = CVSections.from_mapping(_sections().to_dict())

    assert sections == _sections()


def test_from_mapping_normalizes_lists_and_missing_keys() -> None:
    sections = CVSections.from_mapping(
        {
            "summary": "Engineer",
            "technical_skills": ["python", "go"],
            "projects": None,
        }
    )

    assert sections.summary == "Engineer"
    assert sections.technical_skills == "python; go"
    assert sections.projects == ""
    assert sections.experience == ""


def test_from_json_text_parses_the_expected_keys() -> None:
    sections = CVSections.from_json_text(
        '{"summary": "Engineer", "technical_skills": "python", '
        '"experience": "3 years", "projects": "api platform", '
        '"education": "CS degree", "certifications": "AWS", '
        '"languages": "english"}'
    )

    assert sections == CVSections(
        summary="Engineer",
        technical_skills="python",
        experience="3 years",
        projects="api platform",
        education="CS degree",
        certifications="AWS",
        languages="english",
    )


def test_from_json_text_supports_markdown_fences() -> None:
    sections = CVSections.from_json_text(
        '```json\n{"summary": "Engineer", "projects": "api"}\n```'
    )

    assert sections.summary == "Engineer"
    assert sections.projects == "api"


def test_from_json_text_unwraps_optimized_sections() -> None:
    sections = CVSections.from_json_text(
        '{"optimized_sections": {"summary": "Engineer", "projects": "api"}}'
    )

    assert sections.summary == "Engineer"
    assert sections.projects == "api"


def test_from_semantic_profile_maps_every_dimension() -> None:
    profile = SemanticProfile(
        summary="Engineer",
        technical_skills="python",
        experience="3 years",
        projects="api",
        education="CS degree",
        certifications="AWS",
        languages="english",
    )

    assert CVSections.from_semantic_profile(profile) == CVSections(
        summary="Engineer",
        technical_skills="python",
        experience="3 years",
        projects="api",
        education="CS degree",
        certifications="AWS",
        languages="english",
    )


def test_to_text_uses_a_deterministic_order_and_skips_empty_sections() -> None:
    sections = CVSections(
        summary="Engineer",
        technical_skills="python",
        projects="api",
        languages="english",
    )

    assert sections.to_text() == (
        "Summary: Engineer\n"
        "Technical skills: python\n"
        "Projects: api\n"
        "Languages: english"
    )


def test_is_empty_is_false_when_any_section_has_content() -> None:
    assert not CVSections(projects="api").is_empty()


def test_from_json_text_rejects_invalid_json() -> None:
    with pytest.raises(InvalidStructureError):
        CVSections.from_json_text("I cannot extract sections")


def test_from_json_text_rejects_an_empty_structure() -> None:
    with pytest.raises(InvalidStructureError):
        CVSections.from_json_text("{}")


def test_is_immutable() -> None:
    sections = CVSections()

    with pytest.raises(dataclasses.FrozenInstanceError):
        sections.summary = "another"  # type: ignore[misc]
