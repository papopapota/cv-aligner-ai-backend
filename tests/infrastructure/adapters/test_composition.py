import pytest

import src.composition as composition
from src.application.ports.out.llm_agent_port import LLMAgentPort
from src.application.services.optimize_cv_service import OptimizeCVService
from src.composition import build_optimize_cv_use_case
from src.infrastructure.adapters.out.langgraph_orchestrator_adapter import (
    LangGraphOrchestratorAdapter,
)
from src.infrastructure.config import LLMConfigurationError


def test_build_optimize_use_case_fails_clearly_without_an_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_API_KEY", "")
    build_optimize_cv_use_case.cache_clear()

    with pytest.raises(
        LLMConfigurationError,
        match="LLM_API_KEY is not configured",
    ):
        build_optimize_cv_use_case()


def test_build_optimize_use_case_wires_the_real_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    build_optimize_cv_use_case.cache_clear()

    use_case = build_optimize_cv_use_case()
    build_optimize_cv_use_case.cache_clear()

    assert isinstance(use_case, OptimizeCVService)


def test_build_optimize_use_case_wires_the_audit_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("AUDIT_VARIANCE_THRESHOLD", "0.5")
    build_optimize_cv_use_case.cache_clear()

    captured: dict[str, float] = {}
    real_factory = LangGraphOrchestratorAdapter

    def _spy(
        llm_agent: LLMAgentPort,
        variance_threshold: float = 0.35,
        **kwargs: object,
    ) -> LangGraphOrchestratorAdapter:
        captured["variance_threshold"] = variance_threshold
        return real_factory(
            llm_agent,
            variance_threshold=variance_threshold,
            **kwargs,  # type: ignore[arg-type]
        )

    monkeypatch.setattr(
        composition,
        "LangGraphOrchestratorAdapter",
        _spy,
    )

    composition.build_optimize_cv_use_case()
    build_optimize_cv_use_case.cache_clear()

    assert captured["variance_threshold"] == 0.5


def test_build_optimize_use_case_wires_the_ic_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("MATCH_TARGET_IC", "90")
    build_optimize_cv_use_case.cache_clear()

    captured: dict[str, float] = {}
    real_factory = LangGraphOrchestratorAdapter

    def _spy(
        llm_agent: LLMAgentPort,
        variance_threshold: float = 0.35,
        **kwargs: object,
    ) -> LangGraphOrchestratorAdapter:
        captured["ic_target"] = kwargs["ic_target"]  # type: ignore[assignment]
        return real_factory(
            llm_agent,
            variance_threshold=variance_threshold,
            **kwargs,  # type: ignore[arg-type]
        )

    monkeypatch.setattr(
        composition,
        "LangGraphOrchestratorAdapter",
        _spy,
    )

    composition.build_optimize_cv_use_case()
    build_optimize_cv_use_case.cache_clear()

    assert captured["ic_target"] == 90.0
