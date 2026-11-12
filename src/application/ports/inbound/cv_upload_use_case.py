from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.domain.entities.cv import CV


@dataclass(frozen=True, slots=True)
class FileUpload:
    filename: str
    content_type: str
    content: bytes


class CVUploadUseCase(ABC):
    @abstractmethod
    async def execute(self, cv: FileUpload, user_id: int) -> CV:
        """Store the uploaded CV and return its persisted entity."""
