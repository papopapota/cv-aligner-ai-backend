from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.cv import CV


class CVQueryUseCase(ABC):
    @abstractmethod
    async def get(self, cv_id: UUID, user_id: int) -> CV:
        """Return a CV owned by ``user_id`` or raise ``CVNotFoundError``."""

    @abstractmethod
    async def list(self, user_id: int) -> list[CV]:
        """List the CVs owned by ``user_id``."""

    @abstractmethod
    async def get_content(self, cv_id: UUID, user_id: int) -> CV:
        """Return a parsed CV with its extracted content.

        Raise ``CVNotFoundError`` when it does not exist, ``CVFailedError``
        when processing failed and ``CVNotReadyError`` while it is not ready.
        """
