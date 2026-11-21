from abc import ABC, abstractmethod

from src.domain.job_posting_content import JobPostingContent


class ExtractJobDescriptionUseCase(ABC):
    @abstractmethod
    async def execute(self, url: str) -> JobPostingContent:
        """Descarga una oferta y devuelve su contenido estructurado."""
