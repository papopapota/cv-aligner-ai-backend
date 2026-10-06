from abc import ABC, abstractmethod

from src.domain.candidate_cv import CandidateCV
from src.domain.job_description import JobDescription
from src.domain.optimized_cv import OptimizedCV


class WorkflowOrchestratorPort(ABC):
    @abstractmethod
    async def optimize(
        self,
        candidate: CandidateCV,
        job_description: JobDescription,
    ) -> OptimizedCV:
        raise NotImplementedError
