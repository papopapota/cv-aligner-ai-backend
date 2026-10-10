from typing import cast

import httpx2
import pytest
from openai import APIError, AsyncOpenAI

from src.domain.compatibility_score import CompatibilityScore
from src.infrastructure.adapters.out.embedding_match_scorer_adapter import (
    EmbeddingMatchScorerAdapter,
    MatchScorerError,
    chunk_text,
    sanitize_report_text,
)
from src.infrastructure.config import MatchScoringSettings

_HALF = 0.8660254037844386
_UNIT: list[float] = [1.0, 0.0, 0.0]
_MID: list[float] = [0.5, _HALF, 0.0]
_ZERO: list[float] = [0.0, 0.0, 0.0]


class _FakeEmbedding:
    def __init__(self, index: int, embedding: list[float]) -> None:
        self.index = index
        self.embedding = embedding


class _FakeEmbeddingsResponse:
    def __init__(self, data: list[_FakeEmbedding]) -> None:
        self.data = data


class _FakeEmbeddings:
    def __init__(
        self,
        vectors: dict[str, list[float]],
        default: list[float] = [0.0, 0.0, 0.0],
    ) -> None:
        self._vectors = vectors
        self._default = default
        self.calls: list[list[str]] = []

    async def create(self, model: str, input: list[str]) -> _FakeEmbeddingsResponse:
        self.calls.append(list(input))
        data = [
            _FakeEmbedding(i, list(self._vectors.get(text, self._default)))
            for i, text in enumerate(input)
        ]
        return _FakeEmbeddingsResponse(data)


class _FakeClient:
    def __init__(
        self,
        vectors: dict[str, list[float]],
        default: list[float] = [0.0, 0.0, 0.0],
    ) -> None:
        self.embeddings = _FakeEmbeddings(vectors, default)


def _adapter(
    vectors: dict[str, list[float]],
    default: list[float] = [0.0, 0.0, 0.0],
) -> tuple[EmbeddingMatchScorerAdapter, _FakeEmbeddings]:
    fake = _FakeClient(vectors, default)
    settings = MatchScoringSettings(_env_file=None)  # type: ignore[call-arg]
    adapter = EmbeddingMatchScorerAdapter(
        client=cast(AsyncOpenAI, fake),
        settings=settings,
    )
    return adapter, fake.embeddings


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


def test_chunks_text_by_paragraphs_and_size() -> None:
    chunks = chunk_text("aaa bbb ccc", 6)

    assert chunks == ["aaa\nbbb\nccc"]


def test_chunks_merges_short_paragraphs() -> None:
    chunks = chunk_text("first paragraph\nsecond", 100)

    assert chunks == ["first paragraph\nsecond"]


def test_chunks_empty_text() -> None:
    assert chunk_text("   \n", 100) == []


async def test_identical_texts_score_close_to_one() -> None:
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

    assert score.s_cosine == pytest.approx(1.0)
    assert score.d_euclidean == pytest.approx(1.0)
    assert score.a_contextual == pytest.approx(1.0)
    assert score.r_total == pytest.approx(1.0)
    assert score.per_dimension == {
        "experience": pytest.approx(1.0),
        "technical_skills": pytest.approx(1.0),
    }


async def test_exact_r_total_with_fixed_vectors() -> None:
    vectors = {"alpha": _UNIT, "beta": _MID}
    adapter, _ = _adapter(vectors)

    score = await adapter.match("alpha", "beta", {}, {})

    assert score.s_cosine == pytest.approx(0.5)
    assert score.d_euclidean == pytest.approx(0.5)
    assert score.a_contextual == pytest.approx(0.5)
    assert score.r_total == pytest.approx(0.5)
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
    adapter, embeddings = _adapter(
        vectors={"descripcion": _UNIT},
    )

    await adapter.match(candidate_text, job_text, {}, {})

    sent = " ".join(text for call in embeddings.calls for text in call)
    assert "[ocultado]" in sent
    assert "30 years" not in sent
    assert "john@example.com" not in sent
    assert "+34 600 111 222" not in sent


async def test_scores_zero_for_empty_inputs() -> None:
    adapter, _ = _adapter(vectors={})

    score = await adapter.match("", "job", {}, {})

    assert score == CompatibilityScore(0.0, 0.0, 0.0, 0.0)


async def test_skips_dimensions_missing_on_either_side() -> None:
    adapter, _ = _adapter({}, default=_UNIT)

    score = await adapter.match(
        "alpha",
        "beta",
        {"technical_skills": "skill"},
        {"experience": "exp"},
    )

    assert score.per_dimension == {}


async def test_leaves_empty_dimension_text_out() -> None:
    adapter, _ = _adapter({}, default=_UNIT)

    score = await adapter.match(
        "alpha",
        "beta",
        {"technical_skills": "   "},
        {"technical_skills": "skill"},
    )

    assert score.per_dimension == {}


async def test_disjoint_vectors_score_low() -> None:
    vectors = {"alpha": _UNIT, "beta": _ZERO}
    adapter, _ = _adapter(vectors)

    score = await adapter.match("alpha", "beta", {}, {})

    assert score.s_cosine == pytest.approx(0.0)
    assert score.r_total < 0.35


async def test_wraps_embedding_api_errors() -> None:
    class FailingEmbeddings(_FakeEmbeddings):
        async def create(self, model: str, input: list[str]) -> _FakeEmbeddingsResponse:
            raise APIError(
                "boom",
                request=httpx2.Request(method="POST", url="http://example.test"),
                body=None,
            )

    class FailingClient:
        embeddings = FailingEmbeddings(vectors={})

    adapter = EmbeddingMatchScorerAdapter(
        client=cast(AsyncOpenAI, FailingClient()),
        settings=MatchScoringSettings(_env_file=None),  # type: ignore[call-arg]
    )

    with pytest.raises(MatchScorerError):
        await adapter.match("alpha", "beta", {}, {})