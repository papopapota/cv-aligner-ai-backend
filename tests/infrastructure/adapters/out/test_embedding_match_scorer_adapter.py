from collections.abc import Sequence

import pytest

from src.domain.compatibility_score import CompatibilityScore
from src.infrastructure.adapters.out.embedding_match_scorer_adapter import (
    EmbeddingMatchScorerAdapter,
    MatchScorerError,
    sanitize_report_text,
)
from src.infrastructure.adapters.out.openai_embedding_client import (
    EmbeddingClientError,
)
from src.infrastructure.config import MatchScoringSettings

_HALF = 0.8660254037844386
_UNIT: list[float] = [1.0, 0.0, 0.0]
_MID: list[float] = [0.5, _HALF, 0.0]
_ZERO: list[float] = [0.0, 0.0, 0.0]


class _FakeEmbeddingClient:
    def __init__(
        self,
        vectors: dict[str, list[float]],
        default: list[float] = [0.0, 0.0, 0.0],
    ) -> None:
        self._vectors = vectors
        self._default = default
        self.calls: list[list[str]] = []

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [list(self._vectors.get(text, self._default)) for text in texts]


def _adapter(
    vectors: dict[str, list[float]],
    default: list[float] = [0.0, 0.0, 0.0],
) -> tuple[EmbeddingMatchScorerAdapter, _FakeEmbeddingClient]:
    client = _FakeEmbeddingClient(vectors, default)
    settings = MatchScoringSettings(_env_file=None)  # type: ignore[call-arg]
    adapter = EmbeddingMatchScorerAdapter(
        embedding_client=client,
        settings=settings,
    )
    return adapter, client


def test_sanitizes_personal_and_bias_data() -> None:
    text = (
        "John 30 years old. mail me at john@example.com or +34 600 111 222, "
        "born 05/06/1993. nacionalidad: es. foto adjunta."
    )

    result = sanitize_report_text(text)

    assert "[ocultado]" in result
    assert "30 years" not in result
    assert "john@example.com" not in result
    assert "+34 600 111 222" not in result
    assert "05/06/1993" not in result
    assert "nacionalidad" not in result
    assert "foto" not in result


async def test_identical_texts_score_one_hundred() -> None:
    text = "python developer with fastapi"
    vectors = {
        text: _UNIT,
        "skill alpha": _UNIT,
        "skill beta": _UNIT,
        "exp alpha": _UNIT,
        "exp beta": _UNIT,
    }
    adapter, _ = _adapter(vectors)

    score = await adapter.match(
        text,
        text,
        {"technical_skills": "skill alpha", "experience": "exp alpha"},
        {"technical_skills": "skill beta", "experience": "exp beta"},
    )

    assert score.ncos == pytest.approx(1.0)
    assert score.ntfidf == pytest.approx(1.0)
    assert score.neuc == pytest.approx(1.0)
    assert score.ic == pytest.approx(100.0)
    assert score.per_dimension == {
        "experience": pytest.approx(1.0),
        "technical_skills": pytest.approx(1.0),
    }


async def test_exact_metrics_with_fixed_vectors() -> None:
    vectors = {"alpha": _UNIT, "beta": _MID}
    adapter, _ = _adapter(vectors)

    score = await adapter.match("alpha", "beta", {}, {})

    assert score.ncos == pytest.approx(0.5)
    assert score.ntfidf == pytest.approx(0.0)
    assert score.neuc == pytest.approx(0.5)
    assert score.ic == pytest.approx(35.0)
    assert score.per_dimension == {}


async def test_exposes_the_per_dimension_breakdown() -> None:
    vectors = {
        "alpha": _UNIT,
        "beta": _MID,
        "skill alpha": _UNIT,
        "skill beta": _MID,
        "exp alpha": _UNIT,
        "exp beta": _UNIT,
    }
    adapter, _ = _adapter(vectors)

    score = await adapter.match(
        "alpha",
        "beta",
        {"technical_skills": "skill alpha", "experience": "exp alpha"},
        {"technical_skills": "skill beta", "experience": "exp beta"},
    )

    assert score.per_dimension == {
        "experience": pytest.approx(1.0),
        "technical_skills": pytest.approx(0.5),
    }


async def test_sanitizes_texts_before_embedding() -> None:
    candidate_text = "John 30 years old, john@example.com, +34 600 111 222"
    job_text = "descripcion"
    adapter, client = _adapter(
        vectors={"descripcion": _UNIT},
    )

    await adapter.match(candidate_text, job_text, {}, {})

    sent = " ".join(text for call in client.calls for text in call)
    assert "[ocultado]" in sent
    assert "30 years" not in sent
    assert "john@example.com" not in sent
    assert "+34 600 111 222" not in sent


async def test_scores_zero_for_empty_inputs() -> None:
    adapter, _ = _adapter(vectors={})

    score = await adapter.match("", "job", {}, {})

    assert score == CompatibilityScore(0.0, 0.0, 0.0, 0.0)


async def test_batches_global_and_dimension_embeddings_in_one_request() -> None:
    adapter, client = _adapter({}, default=_UNIT)

    score = await adapter.match(
        "global candidate",
        "global job",
        {
            "technical_skills": "skill candidate",
            "education": "degree candidate",
        },
        {
            "technical_skills": "skill job",
            "education": "degree job",
            "certifications": "certification required",
        },
    )

    assert len(client.calls) == 1
    assert client.calls[0] == [
        "global candidate",
        "global job",
        "degree candidate",
        "degree job",
        "skill candidate",
        "skill job",
    ]
    assert score.per_dimension == {
        "certifications": 0.0,
        "education": pytest.approx(1.0),
        "technical_skills": pytest.approx(1.0),
    }


async def test_deduplicates_repeated_embedding_texts() -> None:
    adapter, client = _adapter({"same text": _UNIT})

    score = await adapter.match(
        "same text",
        "same text",
        {"technical_skills": "same text"},
        {"technical_skills": "same text"},
    )

    assert client.calls == [["same text"]]
    assert score.ncos == pytest.approx(1.0)
    assert score.per_dimension == {"technical_skills": pytest.approx(1.0)}


async def test_scores_zero_for_a_requested_dimension_missing_from_the_cv() -> None:
    adapter, _ = _adapter({}, default=_UNIT)

    score = await adapter.match(
        "alpha",
        "beta",
        {"experience": "exp"},
        {"technical_skills": "skill"},
    )

    assert score.per_dimension == {"technical_skills": 0.0}


async def test_omits_dimensions_that_the_job_does_not_request() -> None:
    adapter, _ = _adapter({}, default=_UNIT)

    score = await adapter.match(
        "alpha",
        "beta",
        {"technical_skills": "skill"},
        {"experience": "exp"},
    )

    assert score.per_dimension == {"experience": 0.0}


async def test_scores_zero_when_candidate_dimension_text_is_blank() -> None:
    adapter, _ = _adapter({}, default=_UNIT)

    score = await adapter.match(
        "alpha",
        "beta",
        {"technical_skills": "   "},
        {"technical_skills": "skill"},
    )

    assert score.per_dimension == {"technical_skills": 0.0}


async def test_ignores_empty_job_dimensions() -> None:
    adapter, _ = _adapter({}, default=_UNIT)

    score = await adapter.match(
        "alpha",
        "beta",
        {"technical_skills": "skill"},
        {"technical_skills": "   "},
    )

    assert score.per_dimension == {}


async def test_scores_requested_education_and_certifications() -> None:
    vectors = {
        "degree alpha": _UNIT,
        "degree beta": _UNIT,
    }
    adapter, _ = _adapter(vectors)

    score = await adapter.match(
        "alpha",
        "beta",
        {"education": "degree alpha"},
        {
            "education": "degree beta",
            "certifications": "AWS required",
        },
    )

    assert score.per_dimension == {
        "certifications": 0.0,
        "education": pytest.approx(1.0),
    }


async def test_disjoint_zero_vectors_score_zero() -> None:
    vectors = {"alpha": _UNIT, "beta": _ZERO}
    adapter, _ = _adapter(vectors)

    score = await adapter.match("alpha", "beta", {}, {})

    assert score.ncos == pytest.approx(0.0)
    assert score.ntfidf == pytest.approx(0.0)
    assert score.neuc == pytest.approx(0.0)
    assert score.ic == pytest.approx(0.0)


async def test_wraps_embedding_client_errors() -> None:
    class _FailingEmbeddingClient:
        async def embed(self, texts: Sequence[str]) -> list[list[float]]:
            raise EmbeddingClientError("boom")

    adapter = EmbeddingMatchScorerAdapter(
        embedding_client=_FailingEmbeddingClient(),
        settings=MatchScoringSettings(_env_file=None),  # type: ignore[call-arg]
    )

    with pytest.raises(MatchScorerError):
        await adapter.match("alpha", "beta", {}, {})


async def test_uses_the_configured_weights() -> None:
    vectors = {"alpha": _UNIT, "beta": _MID}
    settings = MatchScoringSettings(  # type: ignore[call-arg]
        _env_file=None,
        weight_ncos=0.2,
        weight_ntfidf=0.3,
        weight_neuc=0.5,
    )
    adapter = EmbeddingMatchScorerAdapter(
        embedding_client=_FakeEmbeddingClient(vectors),
        settings=settings,
    )

    score = await adapter.match("alpha", "beta", {}, {})

    assert score.ic == pytest.approx(
        100.0 * ((0.2 * 0.5) + (0.3 * 0.0) + (0.5 * 0.5))
    )
