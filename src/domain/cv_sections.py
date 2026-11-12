from collections.abc import Mapping
from dataclasses import dataclass

from src.domain.errors import InvalidStructureError
from src.domain.json_extraction import extract_json_object
from src.domain.semantic_profile import SemanticProfile

_SECTION_ORDER = (
    "summary",
    "technical_skills",
    "experience",
    "projects",
    "education",
    "certifications",
    "languages",
)

_SECTION_LABELS = {
    "summary": "Summary",
    "technical_skills": "Technical skills",
    "experience": "Experience",
    "projects": "Projects",
    "education": "Education",
    "certifications": "Certifications",
    "languages": "Languages",
}


def _as_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "; ".join(
            str(item).strip() for item in value if str(item).strip()
        )
    if value is None:
        return ""
    return str(value).strip()


@dataclass(frozen=True, slots=True)
class CVSections:
    summary: str = ""
    technical_skills: str = ""
    experience: str = ""
    projects: str = ""
    education: str = ""
    certifications: str = ""
    languages: str = ""

    @classmethod
    def from_mapping(cls, data: object) -> "CVSections":
        mapping = data if isinstance(data, Mapping) else {}
        return cls(
            **{
                section: _as_text(mapping.get(section))
                for section in _SECTION_ORDER
            }
        )

    @classmethod
    def from_json_text(cls, text: str) -> "CVSections":
        payload = extract_json_object(text)
        if payload is None:
            raise InvalidStructureError(
                "The writer did not return a valid JSON CV."
            )
        candidate: Mapping[str, object] = payload
        for wrapper in ("optimized_sections", "sections", "technical_data"):
            nested = payload.get(wrapper)
            if isinstance(nested, Mapping):
                candidate = nested
                break
        sections = cls.from_mapping(candidate)
        if sections.is_empty():
            raise InvalidStructureError(
                "The writer did not return any CV section."
            )
        return sections

    @classmethod
    def from_semantic_profile(cls, profile: SemanticProfile) -> "CVSections":
        return cls(
            summary=profile.summary,
            technical_skills=profile.technical_skills,
            experience=profile.experience,
            projects=profile.projects,
            education=profile.education,
            certifications=profile.certifications,
            languages=profile.languages,
        )

    def to_dict(self) -> dict[str, str]:
        return {
            section: getattr(self, section) for section in _SECTION_ORDER
        }

    def to_text(self) -> str:
        parts: list[str] = []
        for section in _SECTION_ORDER:
            value = getattr(self, section)
            if value:
                parts.append(f"{_SECTION_LABELS[section]}: {value}")
        return "\n".join(parts)

    def is_empty(self) -> bool:
        return not any(getattr(self, section) for section in _SECTION_ORDER)
