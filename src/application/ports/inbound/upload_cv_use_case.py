from abc import ABC, abstractmethod

from src.application.ports.inbound.cv_upload_use_case import FileUpload
from src.domain.candidate_cv import CandidateCV
from src.domain.job_description import JobDescription

__all__ = ["FileUpload", "UploadCVUseCase"]


class UploadCVUseCase(ABC):
    @abstractmethod
    async def execute(
        self,
        cv: FileUpload,
        job_description: FileUpload,
    ) -> tuple[CandidateCV, JobDescription]:
        raise NotImplementedError
