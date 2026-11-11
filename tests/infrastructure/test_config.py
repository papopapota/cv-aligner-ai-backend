import pytest
from pydantic import ValidationError

from src.application.ports.out.llm_agent_port import AgentRole
from src.domain.audit_rules import DEFAULT_IC_TARGET, MAX_VARIANCE_THRESHOLD
from src.infrastructure.config import (
    AuditSettings,
    LLMSettings,
    MatchScoringSettings,
    S3Settings,
)


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


def test_audit_variance_threshold_defaults_to_the_domain_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AUDIT_VARIANCE_THRESHOLD", raising=False)

    settings = AuditSettings(_env_file=None)  # type: ignore[call-arg]

    assert settings.variance_threshold == MAX_VARIANCE_THRESHOLD


def test_audit_variance_threshold_can_be_overridden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUDIT_VARIANCE_THRESHOLD", "0.5")

    settings = AuditSettings(_env_file=None)  # type: ignore[call-arg]

    assert settings.variance_threshold == 0.5


def _clear_match_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in (
        "MATCH_TARGET_IC",
        "MATCH_WEIGHT_NCOS",
        "MATCH_WEIGHT_NTFIDF",
        "MATCH_WEIGHT_NEUC",
        "MATCH_EMBEDDING_MODEL",
    ):
        monkeypatch.delenv(variable, raising=False)


def test_match_scoring_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_match_env(monkeypatch)

    settings = MatchScoringSettings(_env_file=None)  # type: ignore[call-arg]

    assert settings.target_ic == DEFAULT_IC_TARGET
    assert settings.weight_ncos == 0.50
    assert settings.weight_ntfidf == 0.30
    assert settings.weight_neuc == 0.20
    assert settings.embedding_model == "text-embedding-3-small"


def test_match_scoring_reads_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_match_env(monkeypatch)
    monkeypatch.setenv("MATCH_TARGET_IC", "80")
    monkeypatch.setenv("MATCH_WEIGHT_NCOS", "0.5")
    monkeypatch.setenv("MATCH_WEIGHT_NTFIDF", "0.25")
    monkeypatch.setenv("MATCH_WEIGHT_NEUC", "0.25")
    monkeypatch.setenv("MATCH_EMBEDDING_MODEL", "custom-model")

    settings = MatchScoringSettings(_env_file=None)  # type: ignore[call-arg]

    assert settings.target_ic == 80.0
    assert settings.weight_ncos == 0.5
    assert settings.weight_ntfidf == 0.25
    assert settings.weight_neuc == 0.25
    assert settings.embedding_model == "custom-model"


def test_match_scoring_rejects_weights_that_do_not_sum_to_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_match_env(monkeypatch)
    monkeypatch.setenv("MATCH_WEIGHT_NCOS", "0.6")
    monkeypatch.setenv("MATCH_WEIGHT_NTFIDF", "0.3")
    monkeypatch.setenv("MATCH_WEIGHT_NEUC", "0.2")

    with pytest.raises(ValidationError):
        MatchScoringSettings(_env_file=None)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "variable",
    [
        "MATCH_WEIGHT_NCOS",
        "MATCH_WEIGHT_NTFIDF",
        "MATCH_WEIGHT_NEUC",
        "MATCH_TARGET_IC",
    ],
)
def test_match_scoring_rejects_out_of_range_values(
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
) -> None:
    _clear_match_env(monkeypatch)
    monkeypatch.setenv(variable, "-0.1")

    with pytest.raises(ValidationError):
        MatchScoringSettings(_env_file=None)  # type: ignore[call-arg]


def test_match_scoring_rejects_an_ic_target_above_one_hundred(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_match_env(monkeypatch)
    monkeypatch.setenv("MATCH_TARGET_IC", "100.1")

    with pytest.raises(ValidationError):
        MatchScoringSettings(_env_file=None)  # type: ignore[call-arg]


def _clear_s3_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in (
        "S3_ENDPOINT_URL",
        "S3_REGION",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
        "S3_BUCKET",
        "S3_USE_SSL",
    ):
        monkeypatch.delenv(variable, raising=False)


def test_s3_settings_default_to_localstack(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_s3_env(monkeypatch)

    settings = S3Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.endpoint_url == "http://localhost:4566"
    assert settings.region == "us-east-1"
    assert settings.access_key_id == "test"
    assert settings.secret_access_key == "test"
    assert settings.bucket == "cv-aligner-cvs"
    assert settings.use_ssl is False


def test_s3_settings_read_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_s3_env(monkeypatch)
    monkeypatch.setenv("S3_ENDPOINT_URL", "https://s3.amazonaws.com")
    monkeypatch.setenv("S3_REGION", "eu-west-1")
    monkeypatch.setenv("S3_ACCESS_KEY_ID", "access")
    monkeypatch.setenv("S3_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("S3_BUCKET", "custom-bucket")
    monkeypatch.setenv("S3_USE_SSL", "true")

    settings = S3Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.endpoint_url == "https://s3.amazonaws.com"
    assert settings.region == "eu-west-1"
    assert settings.access_key_id == "access"
    assert settings.secret_access_key == "secret"
    assert settings.bucket == "custom-bucket"
    assert settings.use_ssl is True
