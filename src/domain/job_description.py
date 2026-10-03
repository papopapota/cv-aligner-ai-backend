from dataclasses import dataclass

from src.domain import upload_rules


@dataclass(frozen=True, slots=True)
class JobDescription:
    raw_text: str

    def __post_init__(self) -> None:
        upload_rules.ensure_non_empty_text(self.raw_text)