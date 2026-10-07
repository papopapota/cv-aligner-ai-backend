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
from src.infrastructure.adapters.out.stub_llm_agent_adapter import (
    StubLLMAgentAdapter,
)


def build_upload_cv_use_case() -> UploadCVUseCase:
    return UploadCVService(DocumentParserAdapter())


def build_optimize_cv_use_case() -> OptimizeCVUseCase:
    llm_agent = StubLLMAgentAdapter()
    orchestrator = LangGraphOrchestratorAdapter(llm_agent)
    return OptimizeCVService(orchestrator)
