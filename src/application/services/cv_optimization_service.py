from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from src.application.ports.inbound.cv_optimization_use_case import (
    CVOptimizationUseCase,
)
from src.application.ports.out.cv_repository_port import CVRepositoryPort
from src.application.ports.out.document_exporter_port import DocumentExporterPort
from src.application.ports.out.workflow_orchestrator_port import (
    WorkflowOrchestratorPort,
)
from src.domain.candidate_cv import CandidateCV
from src.domain.errors import CVFailedError, CVNotFoundError, CVNotReadyError
from src.domain.job_description import JobDescription
from src.domain.optimized_cv import OptimizedCV
from src.domain.uploaded_file_metadata import UploadedFileMetadata


class CVOptimizationService(CVOptimizationUseCase):
    def __init__(
        self,
        repository: CVRepositoryPort,
        orchestrator: WorkflowOrchestratorPort,
        exporter: DocumentExporterPort | None = None,
    ) -> None:
        self._repository = repository
        self._orchestrator = orchestrator
        self._exporter = exporter

    async def execute(
        self,
        cv_id: UUID,
        user_id: int,
        job_description_text: str,
    ) -> OptimizedCV:
        cv = await self._repository.get_by_id(cv_id, user_id)
        if cv is None:
            raise CVNotFoundError(f"The CV '{cv_id}' does not exist.")
        if cv.is_failed():
            raise CVFailedError(
                cv.error_code or "PROCESSING_FAILED",
                cv.error_message or "The CV could not be processed.",
            )
        if not cv.is_ready_for_optimization() or cv.structured_cv is None:
            raise CVNotReadyError(
                f"The CV '{cv_id}' is not ready for optimization."
            )

        structured_cv = cv.structured_cv
        technical_data = structured_cv.technical_data
        if technical_data.is_empty():
            raise CVNotReadyError(
                f"The CV '{cv_id}' does not contain technical data."
            )

        metadata = UploadedFileMetadata(
            filename=cv.filename,
            content_type=cv.content_type,
            size_bytes=cv.size_bytes,
            sha256=cv.sha256,
        )
        candidate = CandidateCV(
            metadata=metadata,
            raw_text=technical_data.to_text(),
            technical_profile=technical_data,
        )
        job_description = JobDescription(
            metadata=UploadedFileMetadata.from_job_description_text(
                job_description_text
            ),
            raw_text=job_description_text,
        )

        optimized = await self._orchestrator.optimize(candidate, job_description)
        optimized = replace(
            optimized,
            personal_info=structured_cv.personal_info,
        )

        if self._exporter is not None:
            await self._exporter.export(optimized)

        return optimized
