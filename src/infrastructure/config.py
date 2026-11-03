from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

from src.application.ports.out.llm_agent_port import AgentRole
from src.domain.audit_rules import (
    DEFAULT_R_TOTAL_TARGET,
    MAX_VARIANCE_THRESHOLD,
)


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


class MatchScoringSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MATCH_",
        env_file=".env",
        extra="ignore",
    )

    target_r_total: float = DEFAULT_R_TOTAL_TARGET
    lambda_s_cosine: float = 0.45
    lambda_d_euclidean: float = 0.25
    lambda_a_contextual: float = 0.30
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 512

    @field_validator(
        "lambda_s_cosine",
        "lambda_d_euclidean",
        "lambda_a_contextual",
    )
    @classmethod
    def _validate_lambda(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("Lambdas must be between 0 and 1.")
        return value

    @field_validator("chunk_size")
    @classmethod
    def _validate_chunk_size(cls, value: int) -> int:
        if value < 1:
            raise ValueError("chunk_size must be at least 1.")
        return value

    @field_validator("target_r_total")
    @classmethod
    def _validate_target(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("target_r_total must be between 0 and 1.")
        return value

    @model_validator(mode="after")
    def _validate_lambda_balance(self) -> "MatchScoringSettings":
        total = (
            self.lambda_s_cosine
            + self.lambda_d_euclidean
            + self.lambda_a_contextual
        )
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                "Lambda weights must sum to 1 "
                f"(got {total:.4f})."
            )
        return self


class LLMConfigurationError(RuntimeError):
    pass
