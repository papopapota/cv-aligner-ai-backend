from pydantic_settings import BaseSettings, SettingsConfigDict

from src.application.ports.out.llm_agent_port import AgentRole


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LLM_", env_file=".env")

    api_key: str = ""
    base_url: str = ""
    model: str = "gpt-4o-mini"
    max_tokens: int = 2048
    extractor_max_tokens: int | None = None
    analyzer_max_tokens: int | None = None
    writer_max_tokens: int | None = None
    auditor_max_tokens: int | None = None
    timeout_seconds: float = 60.0

    def max_tokens_by_role(self) -> dict[AgentRole, int]:
        overrides: dict[AgentRole, int] = {}
        if self.extractor_max_tokens is not None:
            overrides[AgentRole.EXTRACTOR] = self.extractor_max_tokens
        if self.analyzer_max_tokens is not None:
            overrides[AgentRole.ANALYZER] = self.analyzer_max_tokens
        if self.writer_max_tokens is not None:
            overrides[AgentRole.WRITER] = self.writer_max_tokens
        if self.auditor_max_tokens is not None:
            overrides[AgentRole.AUDITOR] = self.auditor_max_tokens
        return overrides


class LLMConfigurationError(RuntimeError):
    pass