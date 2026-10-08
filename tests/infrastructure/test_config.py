import pytest

from src.application.ports.out.llm_agent_port import AgentRole
from src.infrastructure.config import LLMSettings


def test_exposes_no_max_token_overrides_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_role_max_tokens_env(monkeypatch)

    settings = LLMSettings(_env_file=None)  # type: ignore[call-arg]

    assert settings.max_tokens_by_role() == {}


def test_exposes_only_the_configured_role_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_role_max_tokens_env(monkeypatch)
    monkeypatch.setenv("LLM_EXTRACTOR_MAX_TOKENS", "800")
    monkeypatch.setenv("LLM_AUDITOR_MAX_TOKENS", "300")

    settings = LLMSettings(_env_file=None)  # type: ignore[call-arg]

    assert settings.max_tokens_by_role() == {
        AgentRole.EXTRACTOR: 800,
        AgentRole.AUDITOR: 300,
    }


def _clear_role_max_tokens_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in (
        "LLM_EXTRACTOR_MAX_TOKENS",
        "LLM_ANALYZER_MAX_TOKENS",
        "LLM_WRITER_MAX_TOKENS",
        "LLM_AUDITOR_MAX_TOKENS",
    ):
        monkeypatch.delenv(variable, raising=False)