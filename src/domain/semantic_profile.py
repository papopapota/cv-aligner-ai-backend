from dataclasses import dataclass

_DIMENSIONS = (
    "technical_skills",
    "experience",
    "education",
    "certifications",
    "languages",
)


@dataclass(frozen=True, slots=True)
class SemanticProfile:
    summary: str = ""
    technical_skills: str = ""
    experience: str = ""
    education: str = ""
    certifications: str = ""
    languages: str = ""

    def as_dimensions(self) -> dict[str, str]:
        return {
            dimension: getattr(self, dimension)
            for dimension in _DIMENSIONS
            if getattr(self, dimension).strip()
        }