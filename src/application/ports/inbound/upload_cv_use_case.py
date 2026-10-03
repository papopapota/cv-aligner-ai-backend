from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.domain.candidate_cv import CandidateCV
from src.domain.job_description import JobDescription


@dataclass(frozen=True, slots=True)
class FileUpload:
    filename: str
    content_type: str
    content: bytes


class UploadCVUseCase(ABC):
    @abstractmethod
    async def execute(
        self,
        cv: FileUpload,
        job_description: JobDescription,
    ) -> CandidateCV:
        raise NotImplementedError