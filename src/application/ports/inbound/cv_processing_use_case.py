from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.cv import CV


class CVProcessingUseCase(ABC):
    @abstractmethod
    async def execute(self, cv_id: UUID) -> CV:
        """Parse and structure a stored CV, updating its lifecycle status."""
