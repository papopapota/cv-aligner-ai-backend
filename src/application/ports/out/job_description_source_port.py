from abc import ABC, abstractmethod

from src.domain.job_posting_content import JobPostingContent


class JobDescriptionSourcePort(ABC):
    @abstractmethod
    async def fetch_content(self, url: str) -> JobPostingContent:
        """Obtiene título, empresa y descripción de una oferta pública."""
