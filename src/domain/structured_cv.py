from collections.abc import Mapping
from dataclasses import dataclass, field

from src.domain.errors import InvalidStructureError
from src.domain.json_extraction import extract_json_object
from src.domain.personal_info import PersonalInfo
from src.domain.semantic_profile import SemanticProfile


@dataclass(frozen=True, slots=True)
class StructuredCV:
    personal_info: PersonalInfo = field(default_factory=PersonalInfo)
    technical_data: SemanticProfile = field(default_factory=SemanticProfile)

    def to_dict(self) -> dict[str, object]:
        return {
            "personal_info": self.personal_info.to_dict(),
            "technical_data": self.technical_data.to_dict(),
        }

    @classmethod
    def from_mapping(cls, data: object) -> "StructuredCV":
        mapping = data if isinstance(data, Mapping) else {}
        technical_payload = mapping.get("technical_data")
        if technical_payload is None:
            technical_payload = mapping.get("technical_profile")
        if technical_payload is None:
            technical_payload = mapping

        return cls(
            personal_info=PersonalInfo.from_mapping(
                mapping.get("personal_info")
            ),
            technical_data=SemanticProfile.from_mapping(technical_payload),
        )

    @classmethod
    def from_json_text(cls, text: str) -> "StructuredCV":
        payload = extract_json_object(text)
        if payload is None:
            raise InvalidStructureError(
                "The structurer did not return a valid JSON CV."
            )
        structured = cls.from_mapping(payload)
        if structured.is_empty():
            raise InvalidStructureError(
                "The structured CV does not contain personal or technical data."
            )
        return structured

    def is_empty(self) -> bool:
        return self.personal_info.is_empty() and self.technical_data.is_empty()
