from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

from src.application.ports.out.llm_agent_port import AgentRole
from src.domain.audit_rules import MAX_VARIANCE_THRESHOLD


class DBSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        extra="ignore",
    )

    host: str = "localhost"
    port: int = 5432
    name: str = "cvaligner"
    user: str = "postgres"
    password: str = "postgresql"

    @property

    def url(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.name,
        )


class AuditSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AUDIT_",
        env_file=".env",
        extra="ignore",
    )

    variance_threshold: float = MAX_VARIANCE_THRESHOLD


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        extra="ignore",
    )

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
