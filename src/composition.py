from __future__ import annotations

import logging
from functools import lru_cache
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.inbound.cv_optimization_use_case import (
    CVOptimizationUseCase,
)
from src.application.ports.inbound.cv_processing_use_case import CVProcessingUseCase
from src.application.ports.inbound.cv_query_use_case import CVQueryUseCase
from src.application.ports.inbound.cv_upload_use_case import CVUploadUseCase
from src.application.ports.inbound.optimize_cv_use_case import OptimizeCVUseCase
from src.application.ports.inbound.upload_cv_use_case import UploadCVUseCase
from src.application.ports.out.cv_repository_port import CVRepositoryPort
from src.application.ports.out.file_storage_port import FileStoragePort
from src.application.ports.out.llm_agent_port import LLMAgentPort
from src.application.ports.out.workflow_orchestrator_port import (
    WorkflowOrchestratorPort,
)
from src.application.services.cv_optimization_service import CVOptimizationService
from src.application.services.cv_processing_service import CVProcessingService
from src.application.services.cv_query_service import CVQueryService
from src.application.services.cv_upload_service import CVUploadService
from src.application.services.optimize_cv_service import OptimizeCVService
from src.application.services.upload_cv_service import UploadCVService
from src.infrastructure.adapters.out.document_parser_adapter import (
    DocumentParserAdapter,
)
from src.infrastructure.adapters.out.embedding_match_scorer_adapter import (
    EmbeddingMatchScorerAdapter,
)
from src.infrastructure.adapters.out.langgraph_orchestrator_adapter import (
    LangGraphOrchestratorAdapter,
)
from src.infrastructure.adapters.out.openai_embedding_client import (
    OpenAIEmbeddingClient,
)
from src.infrastructure.adapters.out.openai_llm_agent_adapter import (
    OpenAILLMAgentAdapter,
)
from src.infrastructure.adapters.out.repositories.cv_repository import (
    SQLAlchemyCVRepository,
)
from src.infrastructure.adapters.out.s3_storage_adapter import S3StorageAdapter
from src.infrastructure.config import (
    AuditSettings,
    LLMConfigurationError,
    LLMSettings,
    MatchScoringSettings,
    S3Settings,
)
from src.infrastructure.database import async_session_factory

logger = logging.getLogger(__name__)


def build_upload_cv_use_case() -> UploadCVUseCase:
    return UploadCVService(DocumentParserAdapter())


def _build_openai_client() -> AsyncOpenAI:
    settings = LLMSettings()
    if not settings.api_key:
        raise LLMConfigurationError(
            "LLM_API_KEY is not configured. Copy .env.example to .env and "
            "set LLM_API_KEY before starting the server."
        )
    if settings.base_url:
        return AsyncOpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.timeout_seconds,
        )
    return AsyncOpenAI(
        api_key=settings.api_key,
        timeout=settings.timeout_seconds,
    )


def build_llm_agent() -> LLMAgentPort:
    settings = LLMSettings()
    return OpenAILLMAgentAdapter(
        client=_build_openai_client(),
        model=settings.model,
        max_tokens=settings.max_tokens,
        max_tokens_by_role=settings.max_tokens_by_role(),
    )


def build_orchestrator() -> WorkflowOrchestratorPort:
    settings = LLMSettings()
    audit_settings = AuditSettings()
    client = _build_openai_client()
    llm_agent = OpenAILLMAgentAdapter(
        client=client,
        model=settings.model,
        max_tokens=settings.max_tokens,
        max_tokens_by_role=settings.max_tokens_by_role(),
    )
    match_settings = MatchScoringSettings()
    embedding_client = OpenAIEmbeddingClient(
        client=client,
        model=match_settings.embedding_model,
    )
    match_scorer = EmbeddingMatchScorerAdapter(
        embedding_client=embedding_client,
        settings=match_settings,
    )
    return LangGraphOrchestratorAdapter(
        llm_agent,
        match_scorer=match_scorer,
        ic_target=match_settings.target_ic,
        variance_threshold=audit_settings.variance_threshold,
    )


@lru_cache(maxsize=1)
def build_optimize_cv_use_case() -> OptimizeCVUseCase:
    return OptimizeCVService(build_orchestrator())


@lru_cache(maxsize=1)
def build_file_storage() -> FileStoragePort:
    return S3StorageAdapter(S3Settings())


def build_cv_repository(session: AsyncSession) -> CVRepositoryPort:
    return SQLAlchemyCVRepository(session)


def build_cv_query_use_case(repository: CVRepositoryPort) -> CVQueryUseCase:
    return CVQueryService(repository)


def build_cv_upload_use_case(
    repository: CVRepositoryPort,
    storage: FileStoragePort,
) -> CVUploadUseCase:
    return CVUploadService(storage, repository)


def build_cv_processing_use_case(
    repository: CVRepositoryPort,
    storage: FileStoragePort,
    llm_agent: LLMAgentPort,
) -> CVProcessingUseCase:
    return CVProcessingService(
        repository,
        storage,
        DocumentParserAdapter(),
        llm_agent,
    )


def build_cv_optimization_use_case(
    repository: CVRepositoryPort,
    orchestrator: WorkflowOrchestratorPort,
) -> CVOptimizationUseCase:
    return CVOptimizationService(repository, orchestrator)


async def process_cv_in_background(cv_id: UUID) -> None:
    try:
        async with async_session_factory() as session:
            service = build_cv_processing_use_case(
                SQLAlchemyCVRepository(session),
                build_file_storage(),
                build_llm_agent(),
            )
            await service.execute(cv_id)
    except Exception:
        logger.exception("Background CV processing failed for %s.", cv_id)
