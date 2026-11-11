from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.ports.inbound.cv_optimization_use_case import (
    CVOptimizationUseCase,
)
from src.application.ports.out.cv_repository_port import CVRepositoryPort
from src.application.ports.out.document_exporter_port import DocumentExporterPort
from src.application.ports.out.workflow_orchestrator_port import (
    WorkflowOrchestratorPort,
)
from src.application.services.cv_optimization_service import CVOptimizationService
from src.domain.cv_status import CVStatus
from src.domain.entities.cv import CV
from src.domain.errors import (
    CVFailedError,
    CVNotFoundError,
    CVNotReadyError,
    EmptyContentError,
)
from src.domain.optimized_cv import OptimizedCV
from src.domain.personal_info import Location, PersonalInfo, ProfessionalLinks
from src.domain.semantic_profile import SemanticProfile
from src.domain.structured_cv import StructuredCV

_USER_ID = 7
_JOB_DESCRIPTION = "We are looking for a Python backend engineer."


def _structured_cv() -> StructuredCV:
    return StructuredCV(
        personal_info=PersonalInfo(
            full_name="Ana Developer",
            headline="Backend Developer",
            email="ana@example.com",
            location=Location(city="Lima", country="Peru"),
            links=ProfessionalLinks(github="github.com/ana"),
        ),
        technical_data=SemanticProfile(
            summary="Backend engineer",
            technical_skills="python, fastapi",
            experience="5 years",
        ),
    )


def _cv(**overrides: object) -> CV:
    values: dict[str, object] = {
        "id": uuid4(),
        "user_id": _USER_ID,
        "s3_key": "users/7/cvs/cv.pdf",
        "filename": "cv.pdf",
        "content_type": "application/pdf",
        "size_bytes": 1024,
        "sha256": "a" * 64,
        "status": CVStatus.PARSED,
        "raw_text": "Ana Developer\nBackend engineer",
        "structured_cv": _structured_cv(),
    }
    values.update(overrides)
    return CV(**values)  # type: ignore[arg-type]


def _optimized() -> OptimizedCV:
    return OptimizedCV(
        content="Optimized backend engineer body.",
        original_variance_score=0.8,
        optimized_variance_score=0.1,
        writer_attempts=1,
    )


@pytest.fixture
def repository() -> AsyncMock:
    return AsyncMock(spec=CVRepositoryPort)


@pytest.fixture
def orchestrator() -> AsyncMock:
    orchestrator = AsyncMock(spec=WorkflowOrchestratorPort)
    orchestrator.optimize.return_value = _optimized()
    return orchestrator


@pytest.fixture
def exporter() -> AsyncMock:
    return AsyncMock(spec=DocumentExporterPort)


@pytest.fixture
def service(
    repository: AsyncMock,
    orchestrator: AsyncMock,
    exporter: AsyncMock,
) -> CVOptimizationService:
    return CVOptimizationService(repository, orchestrator, exporter)


async def test_optimizes_the_parsed_cv_and_restores_personal_info(
    service: CVOptimizationService,
    repository: AsyncMock,
    orchestrator: AsyncMock,
    exporter: AsyncMock,
) -> None:
    cv = _cv()
    repository.get_by_id.return_value = cv

    result = await service.execute(cv.id, _USER_ID, _JOB_DESCRIPTION)

    assert result.content == "Optimized backend engineer body."
    assert result.personal_info == cv.structured_cv.personal_info  # type: ignore[union-attr]
    assert result.full_content.startswith("Ana Developer\nBackend Developer")

    repository.get_by_id.assert_awaited_once_with(cv.id, _USER_ID)
    orchestrator.optimize.assert_awaited_once()
    candidate, job_description = orchestrator.optimize.await_args.args
    assert candidate.raw_text == cv.structured_cv.technical_data.to_text()  # type: ignore[union-attr]
    assert candidate.technical_profile == cv.structured_cv.technical_data  # type: ignore[union-attr]
    assert candidate.metadata.filename == "cv.pdf"
    assert job_description.raw_text == _JOB_DESCRIPTION
    assert job_description.metadata.filename == "job_description.txt"
    exporter.export.assert_awaited_once_with(result)


async def test_does_not_expose_personal_info_to_the_orchestrator(
    service: CVOptimizationService,
    repository: AsyncMock,
    orchestrator: AsyncMock,
) -> None:
    cv = _cv()
    repository.get_by_id.return_value = cv

    await service.execute(cv.id, _USER_ID, _JOB_DESCRIPTION)

    candidate, _ = orchestrator.optimize.await_args.args
    assert "Ana Developer" not in candidate.raw_text
    assert "ana@example.com" not in candidate.raw_text
    assert "Lima" not in candidate.raw_text


async def test_returns_a_missing_cv_error(
    service: CVOptimizationService,
    repository: AsyncMock,
    orchestrator: AsyncMock,
) -> None:
    repository.get_by_id.return_value = None

    with pytest.raises(CVNotFoundError):
        await service.execute(uuid4(), _USER_ID, _JOB_DESCRIPTION)

    orchestrator.optimize.assert_not_awaited()


@pytest.mark.parametrize("status", [CVStatus.UPLOADED, CVStatus.PARSING])
async def test_rejects_a_cv_that_is_not_parsed(
    service: CVOptimizationService,
    repository: AsyncMock,
    orchestrator: AsyncMock,
    status: CVStatus,
) -> None:
    repository.get_by_id.return_value = _cv(status=status)

    with pytest.raises(CVNotReadyError):
        await service.execute(uuid4(), _USER_ID, _JOB_DESCRIPTION)

    orchestrator.optimize.assert_not_awaited()


async def test_reports_the_stored_failure(
    service: CVOptimizationService,
    repository: AsyncMock,
    orchestrator: AsyncMock,
) -> None:
    repository.get_by_id.return_value = _cv(
        status=CVStatus.ERROR,
        error_code="PARSE_FAILED",
        error_message="The CV could not be processed.",
    )

    with pytest.raises(CVFailedError) as error:
        await service.execute(uuid4(), _USER_ID, _JOB_DESCRIPTION)

    assert error.value.error_code == "PARSE_FAILED"
    assert error.value.error_message == "The CV could not be processed."
    orchestrator.optimize.assert_not_awaited()


async def test_rejects_a_parsed_cv_without_structure(
    service: CVOptimizationService,
    repository: AsyncMock,
    orchestrator: AsyncMock,
) -> None:
    repository.get_by_id.return_value = _cv(structured_cv=None)

    with pytest.raises(CVNotReadyError):
        await service.execute(uuid4(), _USER_ID, _JOB_DESCRIPTION)

    orchestrator.optimize.assert_not_awaited()


async def test_rejects_a_cv_without_technical_data(
    service: CVOptimizationService,
    repository: AsyncMock,
    orchestrator: AsyncMock,
) -> None:
    repository.get_by_id.return_value = _cv(
        structured_cv=StructuredCV(
            personal_info=PersonalInfo(full_name="Ana Developer"),
        )
    )

    with pytest.raises(CVNotReadyError):
        await service.execute(uuid4(), _USER_ID, _JOB_DESCRIPTION)

    orchestrator.optimize.assert_not_awaited()


async def test_rejects_an_empty_job_description(
    service: CVOptimizationService,
    repository: AsyncMock,
    orchestrator: AsyncMock,
) -> None:
    repository.get_by_id.return_value = _cv()

    with pytest.raises(EmptyContentError):
        await service.execute(uuid4(), _USER_ID, "   ")

    orchestrator.optimize.assert_not_awaited()


async def test_propagates_orchestrator_errors(
    service: CVOptimizationService,
    repository: AsyncMock,
    orchestrator: AsyncMock,
) -> None:
    repository.get_by_id.return_value = _cv()
    orchestrator.optimize.side_effect = RuntimeError("llm down")

    with pytest.raises(RuntimeError, match="llm down"):
        await service.execute(uuid4(), _USER_ID, _JOB_DESCRIPTION)


async def test_works_without_an_exporter(
    repository: AsyncMock,
    orchestrator: AsyncMock,
) -> None:
    repository.get_by_id.return_value = _cv()
    service = CVOptimizationService(repository, orchestrator)

    result = await service.execute(uuid4(), _USER_ID, _JOB_DESCRIPTION)

    assert result.content == "Optimized backend engineer body."


async def test_satisfies_the_inbound_port(service: CVOptimizationService) -> None:
    assert isinstance(service, CVOptimizationUseCase)
