from abc import ABC, abstractmethod

from src.domain.candidate_cv import CandidateCV
from src.domain.job_description import JobDescription
from src.domain.optimized_cv import OptimizedCV


class OptimizeCVUseCase(ABC):
    @abstractmethod
    async def execute(
        self,
        candidate: CandidateCV,
        job_description: JobDescription,
    ) -> OptimizedCV:
        raise NotImplementedError
