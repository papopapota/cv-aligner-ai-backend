from dataclasses import dataclass

from src.domain import upload_rules
from src.domain.uploaded_file_metadata import UploadedFileMetadata


@dataclass(frozen=True, slots=True)
class CandidateCV:
    metadata: UploadedFileMetadata
    raw_text: str

    def __post_init__(self) -> None:
        upload_rules.ensure_non_empty_text(self.raw_text)