import json
from dataclasses import replace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.ports.inbound.cv_processing_use_case import (
    CVProcessingUseCase,
)
from src.application.ports.out.cv_parser_port import CVParserPort
from src.application.ports.out.cv_repository_port import CVRepositoryPort
from src.application.ports.out.file_storage_port import FileStoragePort
from src.application.ports.out.llm_agent_port import AgentRole, LLMAgentPort
from src.application.services.cv_processing_service import CVProcessingService
from src.domain.cv_status import CVStatus
from src.domain.entities.cv import CV
from src.domain.errors import (
    CVNotFoundError,
    InvalidStructureError,
    StorageError,
    UnsupportedFormatError,
)
from src.domain.personal_info import PersonalInfo
from src.domain.semantic_profile import SemanticProfile
from src.domain.structured_cv import StructuredCV

_CONTENT = b"%PDF-1.7 fake cv bytes"
_RAW_TEXT = "  Ana\tDeveloper \n\n\n Backend  engineer "
_CLEAN_TEXT = "Ana Developer\n\nBackend engineer"
_STRUCTURED_RESPONSE = json.dumps(
    {
        "personal_info": {
            "full_name": "Ana Developer",
            "email": "ana@example.com",
        },
        "technical_data": {
            "summary": "Backend engineer",
            "technical_skills": "python, fastapi",
        },
    }
)


def _cv(**overrides: object) -> CV:
    values: dict[str, object] = {
        "id": uuid4(),
        "user_id": 1,
        "s3_key": "users/1/cvs/cv.pdf",
        "filename": "cv.pdf",
        "content_type": "application/pdf",
        "size_bytes": len(_CONTENT),
        "sha256": "a" * 64,
        "status": CVStatus.UPLOADED,
    }
    values.update(overrides)
    return CV(**values)  # type: ignore[arg-type]


def _structured_cv() -> StructuredCV:
    return StructuredCV(
        personal_info=PersonalInfo(
            full_name="Ana Developer",
            email="ana@example.com",
        ),
        technical_data=SemanticProfile(
            summary="Backend engineer",
            technical_skills="python, fastapi",
        ),
    )


@pytest.fixture
def repository() -> AsyncMock:
    return AsyncMock(spec=CVRepositoryPort)


@pytest.fixture
def storage() -> AsyncMock:
    storage = AsyncMock(spec=FileStoragePort)
    storage.download.return_value = _CONTENT
    return storage


@pytest.fixture
def parser() -> AsyncMock:
    parser = AsyncMock(spec=CVParserPort)
    parser.parse.return_value = _RAW_TEXT
    return parser


@pytest.fixture
def llm_agent() -> AsyncMock:
    llm_agent = AsyncMock(spec=LLMAgentPort)
    llm_agent.complete.return_value = _STRUCTURED_RESPONSE
    return llm_agent


@pytest.fixture
def service(
    repository: AsyncMock,
    storage: AsyncMock,
    parser: AsyncMock,
    llm_agent: AsyncMock,
) -> CVProcessingService:
    return CVProcessingService(repository, storage, parser, llm_agent)


def _wire_success(repository: AsyncMock, cv: CV) -> None:
    repository.get_by_id_unscoped.return_value = cv
    repository.update_status.return_value = replace(
        cv,
        status=CVStatus.PARSING,
    )

    async def save_parsed(
        cv_id: object,
        raw_text: str,
        structured_cv: StructuredCV,
    ) -> CV:
        return replace(
            cv,
            status=CVStatus.PARSED,
            raw_text=raw_text,
            structured_cv=structured_cv,
        )

    repository.save_parsed.side_effect = save_parsed

    async def mark_error(
        cv_id: object,
        error_code: str,
        error_message: str,
    ) -> CV:
        return replace(
            cv,
            status=CVStatus.ERROR,
            error_code=error_code,
            error_message=error_message,
        )

    repository.mark_error.side_effect = mark_error


async def test_parses_and_persists_the_structured_cv(
    service: CVProcessingService,
    repository: AsyncMock,
    storage: AsyncMock,
    parser: AsyncMock,
    llm_agent: AsyncMock,
) -> None:
    cv = _cv()
    _wire_success(repository, cv)

    result = await service.execute(cv.id)

    assert result.status is CVStatus.PARSED
    assert result.raw_text == _CLEAN_TEXT
    assert result.structured_cv == _structured_cv()

    repository.update_status.assert_awaited_once_with(cv.id, CVStatus.PARSING)
    storage.download.assert_awaited_once_with(cv.s3_key)
    parser.parse.assert_awaited_once_with(cv.filename, _CONTENT)
    llm_agent.complete.assert_awaited_once()
    role, prompt = llm_agent.complete.await_args.args
    assert role is AgentRole.EXTRACTOR
    assert _CLEAN_TEXT in prompt
    repository.save_parsed.assert_awaited_once_with(
        cv.id,
        _CLEAN_TEXT,
        _structured_cv(),
    )


async def test_returns_a_missing_cv_error_without_processing(
    service: CVProcessingService,
    repository: AsyncMock,
    storage: AsyncMock,
) -> None:
    repository.get_by_id_unscoped.return_value = None

    with pytest.raises(CVNotFoundError):
        await service.execute(uuid4())

    storage.download.assert_not_awaited()


@pytest.mark.parametrize(
    "status",
    [CVStatus.PARSING, CVStatus.PARSED],
)
async def test_is_idempotent_for_cvs_already_in_progress_or_parsed(
    service: CVProcessingService,
    repository: AsyncMock,
    storage: AsyncMock,
    status: CVStatus,
) -> None:
    cv = _cv(status=status)
    repository.get_by_id_unscoped.return_value = cv

    result = await service.execute(cv.id)

    assert result is cv
    repository.update_status.assert_not_awaited()
    storage.download.assert_not_awaited()


async def test_does_not_reprocess_a_failed_cv(
    service: CVProcessingService,
    repository: AsyncMock,
    storage: AsyncMock,
) -> None:
    cv = _cv(
        status=CVStatus.ERROR,
        error_code="PARSE_FAILED",
        error_message="The CV could not be processed.",
    )
    repository.get_by_id_unscoped.return_value = cv

    result = await service.execute(cv.id)

    assert result is cv
    storage.download.assert_not_awaited()


async def test_marks_the_cv_as_failed_when_the_parser_fails(
    service: CVProcessingService,
    repository: AsyncMock,
    parser: AsyncMock,
) -> None:
    cv = _cv()
    _wire_success(repository, cv)
    parser.parse.side_effect = UnsupportedFormatError("unsupported format")

    result = await service.execute(cv.id)

    assert result.status is CVStatus.ERROR
    assert result.error_code == "UNSUPPORTED_FORMAT"
    repository.save_parsed.assert_not_awaited()
    repository.mark_error.assert_awaited_once_with(
        cv.id,
        "UNSUPPORTED_FORMAT",
        "unsupported format",
    )


async def test_marks_the_cv_as_failed_when_the_storage_fails(
    service: CVProcessingService,
    repository: AsyncMock,
    storage: AsyncMock,
) -> None:
    cv = _cv()
    _wire_success(repository, cv)
    storage.download.side_effect = StorageError("s3 down")

    result = await service.execute(cv.id)

    assert result.status is CVStatus.ERROR
    assert result.error_code == "STORAGE_ERROR"


async def test_marks_the_cv_as_failed_when_the_structurer_returns_invalid_json(
    service: CVProcessingService,
    repository: AsyncMock,
    llm_agent: AsyncMock,
) -> None:
    cv = _cv()
    _wire_success(repository, cv)
    llm_agent.complete.return_value = "not a JSON CV"

    result = await service.execute(cv.id)

    assert result.status is CVStatus.ERROR
    assert result.error_code == "INVALID_STRUCTURE"
    assert result.error_message is not None


async def test_marks_the_cv_as_failed_when_the_extracted_text_is_empty(
    service: CVProcessingService,
    repository: AsyncMock,
    parser: AsyncMock,
) -> None:
    cv = _cv()
    _wire_success(repository, cv)
    parser.parse.return_value = "  \n\t "

    result = await service.execute(cv.id)

    assert result.status is CVStatus.ERROR
    assert result.error_code == "EMPTY_TEXT"


async def test_marks_the_cv_as_failed_on_an_unexpected_error(
    service: CVProcessingService,
    repository: AsyncMock,
    llm_agent: AsyncMock,
) -> None:
    cv = _cv()
    _wire_success(repository, cv)
    llm_agent.complete.side_effect = RuntimeError("provider down")

    result = await service.execute(cv.id)

    assert result.status is CVStatus.ERROR
    assert result.error_code == "PROCESSING_FAILED"
    assert result.error_message == "The CV could not be processed."


async def test_raises_when_the_cv_disappears_while_starting(
    service: CVProcessingService,
    repository: AsyncMock,
    storage: AsyncMock,
) -> None:
    cv = _cv()
    repository.get_by_id_unscoped.return_value = cv
    repository.update_status.return_value = None

    with pytest.raises(CVNotFoundError):
        await service.execute(cv.id)

    storage.download.assert_not_awaited()


async def test_raises_when_the_cv_disappears_while_saving(
    service: CVProcessingService,
    repository: AsyncMock,
) -> None:
    cv = _cv()
    _wire_success(repository, cv)
    repository.save_parsed.side_effect = None
    repository.save_parsed.return_value = None

    with pytest.raises(CVNotFoundError):
        await service.execute(cv.id)


async def test_satisfies_the_inbound_port(service: CVProcessingService) -> None:
    assert isinstance(service, CVProcessingUseCase)


def test_invalid_structure_error_is_not_confused_with_other_errors() -> None:
    from src.application.services.cv_processing_service import _error_details

    code, message = _error_details(InvalidStructureError("bad structure"))

    assert code == "INVALID_STRUCTURE"
    assert message == "bad structure"
