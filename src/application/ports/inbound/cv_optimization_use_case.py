from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.optimized_cv import OptimizedCV


class CVOptimizationUseCase(ABC):
    @abstractmethod
    async def execute(
        self,
        cv_id: UUID,
        user_id: int,
        job_description_text: str,
    ) -> OptimizedCV:
        """Optimize a parsed CV owned by ``user_id`` against a job description."""
