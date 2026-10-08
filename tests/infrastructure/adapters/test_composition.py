import pytest

from src.application.services.optimize_cv_service import OptimizeCVService
from src.composition import build_optimize_cv_use_case
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