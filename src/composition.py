from functools import lru_cache

from openai import AsyncOpenAI

from src.application.ports.inbound.optimize_cv_use_case import OptimizeCVUseCase
from src.application.ports.inbound.upload_cv_use_case import UploadCVUseCase
from src.application.services.optimize_cv_service import OptimizeCVService
from src.application.services.upload_cv_service import UploadCVService
from src.infrastructure.adapters.out.document_parser_adapter import (
    DocumentParserAdapter,
)
from src.infrastructure.adapters.out.langgraph_orchestrator_adapter import (
    LangGraphOrchestratorAdapter,
)
from src.infrastructure.adapters.out.openai_llm_agent_adapter import (
    OpenAILLMAgentAdapter,
)
from src.infrastructure.config import LLMConfigurationError, LLMSettings


def build_upload_cv_use_case() -> UploadCVUseCase:
    return UploadCVService(DocumentParserAdapter())


@lru_cache(maxsize=1)
def build_optimize_cv_use_case() -> OptimizeCVUseCase:
    settings = LLMSettings()
    if not settings.api_key:
        raise LLMConfigurationError(
            "LLM_API_KEY is not configured. Copy .env.example to .env and "
            "set LLM_API_KEY before starting the server."
        )
    if settings.base_url:
        client = AsyncOpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.timeout_seconds,
        )
    else:
        client = AsyncOpenAI(
            api_key=settings.api_key,
            timeout=settings.timeout_seconds,
        )
    llm_agent = OpenAILLMAgentAdapter(
        client=client,
        model=settings.model,
        max_tokens=settings.max_tokens,
        max_tokens_by_role=settings.max_tokens_by_role(),
    )
    orchestrator = LangGraphOrchestratorAdapter(llm_agent)
    return OptimizeCVService(orchestrator)