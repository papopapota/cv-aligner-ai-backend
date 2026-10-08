from unittest.mock import AsyncMock

import pytest

from src.application.services.optimize_cv_service import OptimizeCVService
from src.domain.audit_rules import MAX_VARIANCE_THRESHOLD
from src.domain.candidate_cv import CandidateCV
from src.domain.errors import AuditFailedError
from src.domain.job_description import JobDescription
from src.domain.optimized_cv import OptimizedCV
from src.domain.uploaded_file_metadata import UploadedFileMetadata

_CV_CONTENT = b"%PDF-1.7 fake cv bytes"
_JOB_CONTENT = b"We are looking for a Python developer."


def _candidate() -> CandidateCV:
    return CandidateCV(
        metadata=UploadedFileMetadata.from_bytes(
            "cv.pdf",
            "application/pdf",
            _CV_CONTENT,
        ),
        raw_text="Python developer with 5 years of experience in FastAPI.",
    )


def _job_description() -> JobDescription:
    return JobDescription(
        metadata=UploadedFileMetadata.from_job_description_bytes(
            "job.txt",
            "text/plain",
            _JOB_CONTENT,
        ),
        raw_text="We are looking for a Python developer.",
    )


def _optimized_cv(
    content: str = "Optimized CV body",
    variance_score: float = 0.1,
    writer_attempts: int = 1,
) -> OptimizedCV:
    return OptimizedCV(
        content=content,
        variance_score=variance_score,
        writer_attempts=writer_attempts,
    )


def _service(optimized: OptimizedCV) -> tuple[OptimizeCVService, AsyncMock, AsyncMock]:
    orchestrator = AsyncMock()
    orchestrator.optimize.return_value = optimized
    exporter = AsyncMock()
    return OptimizeCVService(orchestrator, exporter), orchestrator, exporter


async def test_returns_the_orchestrator_result() -> None:
    optimized = _optimized_cv()
    service, orchestrator, _ = _service(optimized)
    candidate = _candidate()
    job_description = _job_description()

    result = await service.execute(candidate, job_description)

    assert result is optimized
    orchestrator.optimize.assert_awaited_once_with(candidate, job_description)


async def test_exports_the_optimized_cv() -> None:
    optimized = _optimized_cv()
    service, _, exporter = _service(optimized)
    candidate = _candidate()
    job_description = _job_description()

    await service.execute(candidate, job_description)

    exporter.export.assert_awaited_once_with(optimized)


async def test_does_not_export_when_the_audit_fails() -> None:
    service, _, exporter = _service(_optimized_cv(variance_score=0.9))
    candidate = _candidate()
    job_description = _job_description()

    with pytest.raises(AuditFailedError):
        await service.execute(candidate, job_description)

    exporter.export.assert_not_awaited()


async def test_raises_when_the_variance_stays_above_the_threshold() -> None:
    service, _, _ = _service(
        _optimized_cv(variance_score=MAX_VARIANCE_THRESHOLD + 0.01)
    )
    candidate = _candidate()
    job_description = _job_description()

    with pytest.raises(AuditFailedError):
        await service.execute(candidate, job_description)


async def test_the_failure_message_reports_the_attempts() -> None:
    service, _, _ = _service(
        _optimized_cv(variance_score=0.9, writer_attempts=3)
    )
    candidate = _candidate()
    job_description = _job_description()

    with pytest.raises(AuditFailedError, match="3 attempts"):
        await service.execute(candidate, job_description)


async def test_works_without_an_exporter() -> None:
    orchestrator = AsyncMock()
    orchestrator.optimize.return_value = _optimized_cv()
    service = OptimizeCVService(orchestrator)
    candidate = _candidate()
    job_description = _job_description()

    result = await service.execute(candidate, job_description)

    assert result.variance_score == 0.1
