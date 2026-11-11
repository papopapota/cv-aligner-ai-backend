from collections.abc import Mapping
from dataclasses import dataclass

from src.domain.errors import InvalidStructureError
from src.domain.json_extraction import extract_json_object

_DIMENSIONS = (
    "technical_skills",
    "experience",
    "projects",
    "education",
    "certifications",
    "languages",
)

_DIMENSION_LABELS = {
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
class SemanticProfile:
    summary: str = ""
    technical_skills: str = ""
    experience: str = ""
    projects: str = ""
    education: str = ""
    certifications: str = ""
    languages: str = ""

    def as_dimensions(self) -> dict[str, str]:
        return {
            dimension: getattr(self, dimension)
            for dimension in _DIMENSIONS
            if getattr(self, dimension).strip()
        }

    def to_dict(self) -> dict[str, str]:
        return {
            "summary": self.summary,
            **{
                dimension: getattr(self, dimension)
                for dimension in _DIMENSIONS
            },
        }

    @classmethod
    def from_mapping(cls, data: object) -> "SemanticProfile":
        mapping = data if isinstance(data, Mapping) else {}
        return cls(
            summary=_as_text(mapping.get("summary")),
            **{
                dimension: _as_text(mapping.get(dimension))
                for dimension in _DIMENSIONS
            },
        )

    @classmethod
    def from_json_text(cls, text: str) -> "SemanticProfile":
        payload = extract_json_object(text)
        if payload is None:
            raise InvalidStructureError(
                "The extractor did not return a valid JSON semantic profile."
            )
        return cls.from_mapping(payload)

    def to_text(self) -> str:
        parts: list[str] = []
        if self.summary:
            parts.append(f"Summary: {self.summary}")
        for dimension in _DIMENSIONS:
            value = getattr(self, dimension)
            if value:
                parts.append(f"{_DIMENSION_LABELS[dimension]}: {value}")
        return "\n".join(parts)

    def is_empty(self) -> bool:
        return not (self.summary or self.as_dimensions())
