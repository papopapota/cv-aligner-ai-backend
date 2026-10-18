import pytest
from pydantic import ValidationError

from src.application.ports.out.llm_agent_port import AgentRole
from src.domain.audit_rules import MAX_VARIANCE_THRESHOLD
from src.infrastructure.config import AuditSettings, LLMSettings, MatchScoringSettings


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
        "MATCH_TARGET_R_TOTAL",
        "MATCH_LAMBDA_S_COSINE",
        "MATCH_LAMBDA_D_EUCLIDEAN",
        "MATCH_LAMBDA_A_CONTEXTUAL",
        "MATCH_EMBEDDING_MODEL",
        "MATCH_CHUNK_SIZE",
    ):
        monkeypatch.delenv(variable, raising=False)


def test_match_scoring_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_match_env(monkeypatch)

    settings = MatchScoringSettings(_env_file=None)  # type: ignore[call-arg]

    assert settings.target_r_total == 0.85
    assert settings.lambda_s_cosine == 0.45
    assert settings.lambda_d_euclidean == 0.25
    assert settings.lambda_a_contextual == 0.30
    assert settings.embedding_model == "text-embedding-3-small"
    assert settings.chunk_size == 512


def test_match_scoring_reads_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_match_env(monkeypatch)
    monkeypatch.setenv("MATCH_TARGET_R_TOTAL", "0.8")
    monkeypatch.setenv("MATCH_LAMBDA_S_COSINE", "0.5")
    monkeypatch.setenv("MATCH_LAMBDA_D_EUCLIDEAN", "0.25")
    monkeypatch.setenv("MATCH_LAMBDA_A_CONTEXTUAL", "0.25")
    monkeypatch.setenv("MATCH_EMBEDDING_MODEL", "custom-model")

    settings = MatchScoringSettings(_env_file=None)  # type: ignore[call-arg]

    assert settings.target_r_total == 0.8
    assert settings.lambda_s_cosine == 0.5
    assert settings.embedding_model == "custom-model"


def test_match_scoring_rejects_lambdas_that_do_not_sum_to_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_match_env(monkeypatch)
    monkeypatch.setenv("MATCH_LAMBDA_S_COSINE", "0.6")
    monkeypatch.setenv("MATCH_LAMBDA_D_EUCLIDEAN", "0.3")
    monkeypatch.setenv("MATCH_LAMBDA_A_CONTEXTUAL", "0.2")

    with pytest.raises(ValidationError):
        MatchScoringSettings(_env_file=None)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "variable",
    [
        "MATCH_LAMBDA_S_COSINE",
        "MATCH_LAMBDA_D_EUCLIDEAN",
        "MATCH_LAMBDA_A_CONTEXTUAL",
        "MATCH_TARGET_R_TOTAL",
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


def test_match_scoring_rejects_a_non_positive_chunk_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_match_env(monkeypatch)
    monkeypatch.setenv("MATCH_CHUNK_SIZE", "0")

    with pytest.raises(ValidationError):
        MatchScoringSettings(_env_file=None)  # type: ignore[call-arg]