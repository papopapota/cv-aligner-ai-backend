from __future__ import annotations

import logging
from uuid import UUID

from src.application.ports.inbound.cv_processing_use_case import (
    CVProcessingUseCase,
)
from src.application.ports.out.cv_parser_port import CVParserPort
from src.application.ports.out.cv_repository_port import CVRepositoryPort
from src.application.ports.out.file_storage_port import FileStoragePort
from src.application.ports.out.llm_agent_port import AgentRole, LLMAgentPort
from src.domain.cv_status import CVStatus
from src.domain.entities.cv import CV
from src.domain.errors import (
    CVNotFoundError,
    CVProcessingError,
    EmptyContentError,
    FileTooLargeError,
    InvalidStructureError,
    InvalidUploadError,
    StorageError,
    UnsupportedFormatError,
)
from src.domain.structured_cv import StructuredCV
from src.domain.text_cleaning import clean_extracted_text

logger = logging.getLogger(__name__)

_STRUCTURER_PROMPT = (
    "Extract the following CV into strict JSON with two keys: "
    '"personal_info" and "technical_data".\n'
    "personal_info may only contain full_name, headline, email, phone, "
    "location {city, country} and links {linkedin, github, portfolio}. "
    "Never include DNI, passport, address, marital status, age, date of birth, "
    "photo, gender, religion, nationality, salary or financial data.\n"
    "technical_data must contain summary, technical_skills, experience, "
    "projects, education, certifications and languages.\n"
    "Return only the JSON object, without markdown.\n\n"
    "CV:\n"
)


class CVProcessingService(CVProcessingUseCase):
    def __init__(
        self,
        repository: CVRepositoryPort,
        storage: FileStoragePort,
        parser: CVParserPort,
        llm_agent: LLMAgentPort,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._parser = parser
        self._llm_agent = llm_agent

    async def execute(self, cv_id: UUID) -> CV:
        cv = await self._repository.get_by_id_unscoped(cv_id)
        if cv is None:
            raise CVNotFoundError(f"The CV '{cv_id}' does not exist.")
        if cv.status is not CVStatus.UPLOADED:
            return cv

        parsing = await self._repository.update_status(cv_id, CVStatus.PARSING)
        if parsing is None:
            raise CVNotFoundError(f"The CV '{cv_id}' does not exist.")

        try:
            content = await self._storage.download(cv.s3_key)
            parsed_text = await self._parser.parse(cv.filename, content)
            raw_text = clean_extracted_text(parsed_text)
            if not raw_text.strip():
                raise CVProcessingError(
                    "EMPTY_TEXT",
                    "The CV does not contain extractable text.",
                )
            structured_cv = await self._structure(raw_text)
        except Exception as exc:
            error_code, error_message = _error_details(exc)
            logger.exception(
                "CV processing failed for %s with code %s.",
                cv_id,
                error_code,
            )
            failed = await self._repository.mark_error(
                cv_id,
                error_code,
                error_message,
            )
            if failed is None:
                raise CVNotFoundError(
                    f"The CV '{cv_id}' does not exist."
                ) from exc
            return failed

        saved = await self._repository.save_parsed(
            cv_id,
            raw_text,
            structured_cv,
        )
        if saved is None:
            raise CVNotFoundError(f"The CV '{cv_id}' does not exist.")
        return saved

    async def _structure(self, raw_text: str) -> StructuredCV:
        response = await self._llm_agent.complete(
            AgentRole.EXTRACTOR,
            _STRUCTURER_PROMPT + raw_text,
        )
        return StructuredCV.from_json_text(response)


def _error_details(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, CVProcessingError):
        return exc.error_code, exc.error_message
    if isinstance(exc, InvalidStructureError):
        return "INVALID_STRUCTURE", str(exc)
    if isinstance(exc, UnsupportedFormatError):
        return "UNSUPPORTED_FORMAT", str(exc)
    if isinstance(exc, FileTooLargeError):
        return "FILE_TOO_LARGE", str(exc)
    if isinstance(exc, EmptyContentError):
        return "EMPTY_CONTENT", str(exc)
    if isinstance(exc, InvalidUploadError):
        return "INVALID_UPLOAD", str(exc)
    if isinstance(exc, StorageError):
        return "STORAGE_ERROR", str(exc)
    return "PROCESSING_FAILED", "The CV could not be processed."
