from src.application.ports.inbound.optimize_cv_use_case import OptimizeCVUseCase
from src.application.ports.out.document_exporter_port import DocumentExporterPort
from src.application.ports.out.workflow_orchestrator_port import (
    WorkflowOrchestratorPort,
)
from src.domain.candidate_cv import CandidateCV
from src.domain.errors import AuditFailedError
from src.domain.job_description import JobDescription
from src.domain.optimized_cv import OptimizedCV


class OptimizeCVService(OptimizeCVUseCase):
    def __init__(
        self,
        orchestrator: WorkflowOrchestratorPort,
        exporter: DocumentExporterPort | None = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._exporter = exporter

    async def execute(
        self,
        candidate: CandidateCV,
        job_description: JobDescription,
    ) -> OptimizedCV:
        optimized = await self._orchestrator.optimize(candidate, job_description)

        if not optimized.is_within_threshold():
            raise AuditFailedError(
                "The optimized CV did not pass the variance audit after "
                f"{optimized.writer_attempts} attempts."
            )

        if self._exporter is not None:
            await self._exporter.export(optimized)

        return optimized
