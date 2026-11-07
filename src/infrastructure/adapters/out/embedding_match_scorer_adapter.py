import logging
import re
import time
from collections.abc import Mapping

from src.application.ports.out.match_scorer_port import MatchScorerPort
from src.domain.compatibility_metrics import (
    CompatibilityWeights,
    compatibility_index,
    normalized_cosine,
    normalized_euclidean,
)
from src.domain.compatibility_score import CompatibilityScore
from src.domain.tfidf import normalized_tfidf_relevance
from src.infrastructure.adapters.out.openai_embedding_client import (
    EmbeddingClient,
    EmbeddingClientError,
)
from src.infrastructure.config import MatchScoringSettings

logger = logging.getLogger(__name__)

_SANITIZERS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b[\w.+-]+@[\w.-]+\.\w{2,}\b"), "[ocultado]"),
    (
        re.compile(
            r"\b\d{1,2}\s*(?:a[ñn]os(?:\s+de\s+edad)?|years(?:\s+old)?)\b",
            re.IGNORECASE,
        ),
        "[ocultado]",
    ),
    (re.compile(r"\b\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}\b"), "[ocultado]"),
    (
        re.compile(
            r"\b(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{2,3}\)[\s.-]?)?"
            r"\d{3}[\s.-]?\d{3}[\s.-]?\d{2,4}\b"
        ),
        "[ocultado]",
    ),
)

_BIAS_TOKENS: dict[str, str] = {
    "género": "[ocultado]",
    "genero": "[ocultado]",
    "sexo": "[ocultado]",
    "nacionalidad": "[ocultado]",
    "estado civil": "[ocultado]",
    "marital status": "[ocultado]",
    "fotografía": "[ocultado]",
    "fotografia": "[ocultado]",
    "photo": "[ocultado]",
    "foto": "[ocultado]",
}


def sanitize_report_text(text: str) -> str:
    for pattern, replacement in _SANITIZERS:
        text = pattern.sub(replacement, text)
    for token, replacement in _BIAS_TOKENS.items():
        text = re.sub(
            rf"\b{re.escape(token)}\b",
            replacement,
            text,
            flags=re.IGNORECASE,
        )
    return text


class MatchScorerError(RuntimeError):
    pass


class EmbeddingMatchScorerAdapter(MatchScorerPort):
    def __init__(
        self,
        embedding_client: EmbeddingClient,
        settings: MatchScoringSettings,
    ) -> None:
        self._embedding_client = embedding_client
        self._settings = settings
        self._weights = CompatibilityWeights(
            ncos=settings.weight_ncos,
            ntfidf=settings.weight_ntfidf,
            neuc=settings.weight_neuc,
        )

    async def match(
        self,
        candidate_text: str,
        job_text: str,
        candidate_dimensions: Mapping[str, str],
        job_dimensions: Mapping[str, str],
    ) -> CompatibilityScore:
        candidate_text = sanitize_report_text(candidate_text)
        job_text = sanitize_report_text(job_text)

        if not candidate_text or not job_text:
            return CompatibilityScore(
                ncos=0.0,
                ntfidf=0.0,
                neuc=0.0,
                ic=0.0,
            )

        per_dimension: dict[str, float] = {}
        dimension_texts: list[tuple[str, str, str]] = []
        texts = [candidate_text, job_text]
        for dimension in sorted(job_dimensions):
            job_dimension_text = sanitize_report_text(
                job_dimensions[dimension].strip()
            )
            if not job_dimension_text:
                continue
            candidate_dimension_text = sanitize_report_text(
                candidate_dimensions.get(dimension, "").strip()
            )
            if not candidate_dimension_text:
                per_dimension[dimension] = 0.0
                continue
            dimension_texts.append(
                (dimension, candidate_dimension_text, job_dimension_text)
            )
            texts.extend([candidate_dimension_text, job_dimension_text])

        unique_texts = list(dict.fromkeys(texts))
        started_at = time.perf_counter()
        try:
            embedded = await self._embedding_client.embed(unique_texts)
        except EmbeddingClientError as exc:
            raise MatchScorerError(str(exc)) from exc
        logger.info(
            "Embedding batch finished: texts=%d duration=%.3fs",
            len(unique_texts),
            time.perf_counter() - started_at,
        )
        vectors = dict(zip(unique_texts, embedded, strict=True))

        candidate_vector = vectors[candidate_text]
        job_vector = vectors[job_text]
        ncos = normalized_cosine(candidate_vector, job_vector)
        neuc = normalized_euclidean(candidate_vector, job_vector)
        ntfidf = normalized_tfidf_relevance(candidate_text, job_text)
        ic = compatibility_index(ncos, ntfidf, neuc, self._weights)

        for (
            dimension,
            candidate_dimension_text,
            job_dimension_text,
        ) in dimension_texts:
            per_dimension[dimension] = normalized_cosine(
                vectors[candidate_dimension_text],
                vectors[job_dimension_text],
            )

        return CompatibilityScore(
            ncos=ncos,
            ntfidf=ntfidf,
            neuc=neuc,
            ic=ic,
            per_dimension=per_dimension,
        )
