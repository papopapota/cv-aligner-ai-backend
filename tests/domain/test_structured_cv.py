import pytest

from src.domain.errors import InvalidStructureError
from src.domain.personal_info import Location, PersonalInfo, ProfessionalLinks
from src.domain.semantic_profile import SemanticProfile
from src.domain.structured_cv import StructuredCV


def _payload() -> dict[str, object]:
    return {
        "personal_info": {
            "full_name": "Ana Developer",
            "headline": "Backend Developer",
            "email": "ana@example.com",
            "phone": "+51 999 999 999",
            "location": {"city": "Lima", "country": "Peru"},
            "links": {
                "linkedin": "linkedin.com/in/ana",
                "github": "github.com/ana",
                "portfolio": "ana.dev",
            },
        },
        "technical_data": {
            "summary": "Backend engineer",
            "technical_skills": "python, fastapi",
            "experience": "5 years",
            "projects": "cv-aligner",
            "education": "CS degree",
            "certifications": "AWS",
            "languages": "english, spanish",
        },
    }


def test_from_json_text_parses_both_blocks() -> None:
    import json

    structured = StructuredCV.from_json_text(json.dumps(_payload()))

    assert structured.personal_info == PersonalInfo(
        full_name="Ana Developer",
        headline="Backend Developer",
        email="ana@example.com",
        phone="+51 999 999 999",
        location=Location(city="Lima", country="Peru"),
        links=ProfessionalLinks(
            linkedin="linkedin.com/in/ana",
            github="github.com/ana",
            portfolio="ana.dev",
        ),
    )
    assert structured.technical_data == SemanticProfile(
        summary="Backend engineer",
        technical_skills="python, fastapi",
        experience="5 years",
        projects="cv-aligner",
        education="CS degree",
        certifications="AWS",
        languages="english, spanish",
    )


def test_from_json_text_drops_forbidden_personal_fields() -> None:
    import json

    payload = _payload()
    personal = payload["personal_info"]
    assert isinstance(personal, dict)
    personal.update(
        {
            "dni": "12345678",
            "address": "Calle Falsa 123",
            "age": 30,
            "photo": "base64...",
            "nationality": "Peruvian",
            "salary": "100k",
        }
    )

    structured = StructuredCV.from_json_text(json.dumps(payload))

    serialized = structured.personal_info.to_dict()
    assert "dni" not in serialized
    assert "address" not in serialized
    assert "age" not in serialized
    assert "photo" not in serialized
    assert "nationality" not in serialized
    assert "salary" not in serialized


def test_from_json_text_supports_markdown_fences_and_extra_text() -> None:
    structured = StructuredCV.from_json_text(
        "Here is the result:\n```json\n"
        '{"personal_info": {"full_name": "Ana"}, '
        '"technical_data": {"summary": "Engineer"}}\n'
        "```"
    )

    assert structured.personal_info.full_name == "Ana"
    assert structured.technical_data.summary == "Engineer"


def test_from_json_text_supports_a_legacy_flat_technical_payload() -> None:
    structured = StructuredCV.from_json_text(
        '{"summary": "Engineer", "technical_skills": "python"}'
    )

    assert structured.personal_info == PersonalInfo()
    assert structured.technical_data.summary == "Engineer"
    assert structured.technical_data.technical_skills == "python"


def test_from_json_text_rejects_invalid_json() -> None:
    with pytest.raises(InvalidStructureError):
        StructuredCV.from_json_text("I cannot extract this CV")


def test_from_json_text_rejects_an_empty_structure() -> None:
    with pytest.raises(InvalidStructureError):
        StructuredCV.from_json_text("{}")


def test_to_dict_round_trips_through_from_mapping() -> None:
    structured = StructuredCV.from_mapping(_payload())

    assert StructuredCV.from_mapping(structured.to_dict()) == structured


def test_to_sections_maps_the_technical_dimensions() -> None:
    structured = StructuredCV.from_mapping(_payload())

    assert structured.to_sections().to_dict() == {
        "summary": "Backend engineer",
        "technical_skills": "python, fastapi",
        "experience": "5 years",
        "projects": "cv-aligner",
        "education": "CS degree",
        "certifications": "AWS",
        "languages": "english, spanish",
    }


def test_is_empty() -> None:
    assert StructuredCV().is_empty()
    assert not StructuredCV(
        personal_info=PersonalInfo(full_name="Ana")
    ).is_empty()
    assert not StructuredCV(
        technical_data=SemanticProfile(summary="Engineer")
    ).is_empty()
