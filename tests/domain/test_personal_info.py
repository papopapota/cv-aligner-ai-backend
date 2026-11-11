import dataclasses

import pytest

from src.domain.personal_info import (
    FORBIDDEN_PERSONAL_KEYS,
    Location,
    PersonalInfo,
    ProfessionalLinks,
    forbidden_keys_present,
    render_personal_header,
)


def _full_payload() -> dict[str, object]:
    return {
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
    }


def test_from_mapping_keeps_allowed_personal_fields() -> None:
    info = PersonalInfo.from_mapping(_full_payload())

    assert info.full_name == "Ana Developer"
    assert info.headline == "Backend Developer"
    assert info.email == "ana@example.com"
    assert info.phone == "+51 999 999 999"
    assert info.location == Location(city="Lima", country="Peru")
    assert info.links == ProfessionalLinks(
        linkedin="linkedin.com/in/ana",
        github="github.com/ana",
        portfolio="ana.dev",
    )


def test_from_mapping_supports_common_aliases() -> None:
    info = PersonalInfo.from_mapping(
        {
            "name": "Ana Developer",
            "role": "Backend Developer",
            "telephone": "+51 999 999 999",
            "links": {"website": "ana.dev"},
        }
    )

    assert info.full_name == "Ana Developer"
    assert info.headline == "Backend Developer"
    assert info.phone == "+51 999 999 999"
    assert info.links.portfolio == "ana.dev"


def test_to_dict_only_exposes_allowed_fields() -> None:
    info = PersonalInfo.from_mapping(_full_payload())

    assert info.to_dict() == _full_payload()


def test_forbidden_keys_are_detected_case_insensitively() -> None:
    payload = {
        "full_name": "Ana Developer",
        "DNI": "12345678",
        "Age": 30,
        "salary_expectations": "100k",
    }

    assert forbidden_keys_present(payload) == {"dni", "age", "salary_expectations"}


def test_forbidden_keys_are_never_mapped_to_the_domain_object() -> None:
    payload = {
        **_full_payload(),
        "dni": "12345678",
        "passport": "A123456",
        "address": "Calle Falsa 123",
        "age": 30,
        "date_of_birth": "1990-01-01",
        "photo": "base64...",
        "gender": "female",
        "religion": "none",
        "nationality": "Peruvian",
        "salary": "100k",
        "location": {
            "city": "Lima",
            "country": "Peru",
            "address": "Calle Falsa 123",
        },
        "links": {
            "linkedin": "linkedin.com/in/ana",
            "tax_id": "12345678",
        },
    }

    info = PersonalInfo.from_mapping(payload)
    serialized = info.to_dict()

    assert "dni" not in serialized
    assert "passport" not in serialized
    assert "address" not in serialized
    assert "age" not in serialized
    assert "photo" not in serialized
    assert "salary" not in serialized

    location = serialized["location"]
    links = serialized["links"]
    assert isinstance(location, dict)
    assert isinstance(links, dict)
    assert "address" not in location
    assert "tax_id" not in links


def test_from_mapping_ignores_non_mapping_payloads() -> None:
    assert PersonalInfo.from_mapping("not a mapping") == PersonalInfo()


def test_is_empty() -> None:
    assert PersonalInfo().is_empty()
    assert not PersonalInfo(full_name="Ana").is_empty()
    assert not PersonalInfo(location=Location(city="Lima")).is_empty()
    assert not PersonalInfo(links=ProfessionalLinks(github="github.com/ana")).is_empty()


def test_render_personal_header_uses_only_non_empty_fields() -> None:
    info = PersonalInfo(
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

    assert render_personal_header(info) == (
        "Ana Developer\n"
        "Backend Developer\n"
        "ana@example.com | +51 999 999 999 | Lima, Peru\n"
        "linkedin.com/in/ana | github.com/ana | ana.dev"
    )


def test_render_personal_header_omits_missing_sections() -> None:
    info = PersonalInfo(full_name="Ana Developer", email="ana@example.com")

    assert render_personal_header(info) == "Ana Developer\nana@example.com"


def test_render_personal_header_is_empty_for_empty_info() -> None:
    assert render_personal_header(None) == ""
    assert render_personal_header(PersonalInfo()) == ""


def test_forbidden_keys_include_sensitive_documents_and_demographics() -> None:
    expected = {
        "dni",
        "passport",
        "address",
        "marital_status",
        "age",
        "date_of_birth",
        "photo",
        "gender",
        "religion",
        "nationality",
        "salary",
    }

    assert expected <= FORBIDDEN_PERSONAL_KEYS


def test_is_immutable() -> None:
    info = PersonalInfo()

    with pytest.raises(dataclasses.FrozenInstanceError):
        info.email = "ana@example.com"  # type: ignore[misc]
