from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

from src.application.ports.out.llm_agent_port import AgentRole
from src.domain.audit_rules import DEFAULT_IC_TARGET, MAX_VARIANCE_THRESHOLD


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

    target_ic: float = DEFAULT_IC_TARGET
    weight_ncos: float = 0.50
    weight_ntfidf: float = 0.30
    weight_neuc: float = 0.20
    embedding_model: str = "text-embedding-3-small"

    @field_validator("weight_ncos", "weight_ntfidf", "weight_neuc")
    @classmethod
    def _validate_weight(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("IC weights must be between 0 and 1.")
        return value

    @field_validator("target_ic")
    @classmethod
    def _validate_target(cls, value: float) -> float:
        if not 0.0 <= value <= 100.0:
            raise ValueError("target_ic must be between 0 and 100.")
        return value

    @model_validator(mode="after")
    def _validate_weight_balance(self) -> "MatchScoringSettings":
        total = self.weight_ncos + self.weight_ntfidf + self.weight_neuc
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                "IC weights must sum to 1 "
                f"(got {total:.4f})."
            )
        return self


class S3Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="S3_",
        env_file=".env",
        extra="ignore",
    )

    endpoint_url: str = "http://localhost:4566"
    region: str = "us-east-1"
    access_key_id: str = "test"
    secret_access_key: str = "test"
    bucket: str = "cv-aligner-cvs"
    use_ssl: bool = False


class LLMConfigurationError(RuntimeError):
    pass


class CORSSettings(BaseSettings):
    """CORS configuration driven by the ``CORS_ORIGINS`` environment variable."""

    model_config = SettingsConfigDict(
        env_prefix="CORS_",
        env_file=".env",
        extra="ignore",
    )

    origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def allow_origins(self) -> list[str]:
        return [origin.strip() for origin in self.origins.split(",") if origin.strip()]
