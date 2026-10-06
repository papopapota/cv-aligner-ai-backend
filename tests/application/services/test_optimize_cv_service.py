from unittest.mock import AsyncMock

import pytest

from src.application.services.optimize_cv_service import OptimizeCVService
from src.domain.audit_rules import MAX_VARIANCE_THRESHOLD
from src.domain.errors import AuditFailedError
from src.domain.optimized_cv import OptimizedCV

_CANDIDATE = object()
_JOB_DESCRIPTION = object()


def _optimized_cv(**overrides: object) -> OptimizedCV:
    fields: dict[str, object] = {
        "content": "Optimized CV body",
        "variance_score": 0.1,
        "writer_attempts": 1,
    }
    fields.update(overrides)
    return OptimizedCV(**fields)


def _service(optimized: OptimizedCV) -> tuple[OptimizeCVService, AsyncMock, AsyncMock]:
    orchestrator = AsyncMock()
    orchestrator.optimize.return_value = optimized
    exporter = AsyncMock()
    return OptimizeCVService(orchestrator, exporter), orchestrator, exporter


async def test_returns_the_orchestrator_result() -> None:
    optimized = _optimized_cv()
    service, orchestrator, _ = _service(optimized)

    result = await service.execute(_CANDIDATE, _JOB_DESCRIPTION)

    assert result is optimized
    orchestrator.optimize.assert_awaited_once_with(_CANDIDATE, _JOB_DESCRIPTION)


async def test_exports_the_optimized_cv() -> None:
    optimized = _optimized_cv()
    service, _, exporter = _service(optimized)

    await service.execute(_CANDIDATE, _JOB_DESCRIPTION)

    exporter.export.assert_awaited_once_with(optimized)


async def test_does_not_export_when_the_audit_fails() -> None:
    service, _, exporter = _service(_optimized_cv(variance_score=0.9))

    with pytest.raises(AuditFailedError):
        await service.execute(_CANDIDATE, _JOB_DESCRIPTION)

    exporter.export.assert_not_awaited()


async def test_raises_when_the_variance_stays_above_the_threshold() -> None:
    service, _, _ = _service(
        _optimized_cv(variance_score=MAX_VARIANCE_THRESHOLD + 0.01)
    )

    with pytest.raises(AuditFailedError):
        await service.execute(_CANDIDATE, _JOB_DESCRIPTION)


async def test_the_failure_message_reports_the_attempts() -> None:
    service, _, _ = _service(
        _optimized_cv(variance_score=0.9, writer_attempts=3)
    )

    with pytest.raises(AuditFailedError, match="3 attempts"):
        await service.execute(_CANDIDATE, _JOB_DESCRIPTION)


async def test_works_without_an_exporter() -> None:
    orchestrator = AsyncMock()
    orchestrator.optimize.return_value = _optimized_cv()
    service = OptimizeCVService(orchestrator)

    result = await service.execute(_CANDIDATE, _JOB_DESCRIPTION)

    assert result.variance_score == 0.1
