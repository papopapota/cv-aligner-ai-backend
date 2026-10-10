import re
from collections.abc import Mapping

import numpy as np
from openai import APIError, AsyncOpenAI

from src.application.ports.out.match_scorer_port import MatchScorerPort
from src.domain.compatibility_score import CompatibilityScore
from src.infrastructure.config import MatchScoringSettings

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


def chunk_text(text: str, chunk_size: int) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in text.splitlines() if paragraph.strip()]
    if not paragraphs:
        return []
    chunks: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        if not buffer:
            buffer = paragraph
        elif len(buffer) + 1 + len(paragraph) <= chunk_size:
            buffer = f"{buffer}\n{paragraph}"
        else:
            chunks.append(buffer)
            buffer = paragraph
    if buffer:
        chunks.append(buffer)
    result: list[str] = []
    for chunk in chunks:
        split = _split_oversized(chunk, chunk_size)
        if split:
            result.append(split)
    return result


def _split_oversized(text: str, chunk_size: int) -> str:
    if len(text) <= chunk_size:
        return text
    pieces: list[str] = []
    for word in text.split():
        if not pieces or len(pieces[-1]) + 1 + len(word) > chunk_size:
            pieces.append(word)
        else:
            pieces[-1] = f"{pieces[-1]} {word}"
    return "\n".join(pieces)


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    left_norm = float(np.linalg.norm(left))
    right_norm = float(np.linalg.norm(right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return float(np.dot(left, right) / (left_norm * right_norm))


def _machine_attention(candidate: list[np.ndarray], job: list[np.ndarray]) -> float:
    if not candidate or not job:
        return 0.0
    scores = np.asarray(
        [[_cosine(c, j) for j in job] for c in candidate],
        dtype=float,
    )
    shifted = scores - scores.max(axis=1, keepdims=True)
    exponentials = np.exp(shifted)
    weights = exponentials / exponentials.sum(axis=1, keepdims=True)
    attended = (weights * scores).sum(axis=1)
    return float(attended.mean())


class MatchScorerError(RuntimeError):
    pass


class EmbeddingMatchScorerAdapter(MatchScorerPort):
    def __init__(self, client: AsyncOpenAI, settings: MatchScoringSettings) -> None:
        self._client = client
        self._settings = settings

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
                s_cosine=0.0,
                d_euclidean=0.0,
                a_contextual=0.0,
                r_total=0.0,
            )

        candidate_vector, job_vector = await self._pair_embeddings(
            candidate_text, job_text
        )

        s_cosine = _cosine(candidate_vector, job_vector)
        euclidean = float(np.linalg.norm(candidate_vector - job_vector))
        d_euclidean = 1.0 / (1.0 + euclidean)

        candidate_vectors = await self._batch_embeddings(
            chunk_text(candidate_text, self._settings.chunk_size)
        )
        job_vectors = await self._batch_embeddings(
            chunk_text(job_text, self._settings.chunk_size)
        )
        a_contextual = _machine_attention(candidate_vectors, job_vectors)

        per_dimension = await self._score_dimensions(
            candidate_dimensions,
            job_dimensions,
        )

        r_total = (
            self._settings.lambda_s_cosine * s_cosine
            + self._settings.lambda_d_euclidean * d_euclidean
            + self._settings.lambda_a_contextual * a_contextual
        )
        r_total = min(max(r_total, 0.0), 1.0)

        return CompatibilityScore(
            s_cosine=s_cosine,
            d_euclidean=d_euclidean,
            a_contextual=a_contextual,
            r_total=r_total,
            per_dimension=per_dimension,
        )

    async def _pair_embeddings(
        self,
        left_text: str,
        right_text: str,
    ) -> tuple[np.ndarray, np.ndarray]:
        left, right = await self._batch_embeddings([left_text, right_text])
        return left, right

    async def _batch_embeddings(self, texts: list[str]) -> list[np.ndarray]:
        if not texts:
            return []
        try:
            response = await self._client.embeddings.create(
                model=self._settings.embedding_model,
                input=texts,
            )
        except APIError as exc:
            raise MatchScorerError(
                f"Embedding call failed on model "
                f"'{self._settings.embedding_model}': {exc}"
            ) from exc
        ordered = sorted(response.data, key=lambda item: item.index)
        return [np.asarray(item.embedding, dtype=float) for item in ordered]

    async def _score_dimensions(
        self,
        candidate_dimensions: Mapping[str, str],
        job_dimensions: Mapping[str, str],
    ) -> dict[str, float]:
        per_dimension: dict[str, float] = {}
        shared = set(candidate_dimensions) & set(job_dimensions)
        for dimension in sorted(shared):
            candidate_text = candidate_dimensions[dimension].strip()
            job_text = job_dimensions[dimension].strip()
            if not candidate_text or not job_text:
                continue
            candidate_vector, job_vector = await self._pair_embeddings(
                sanitize_report_text(candidate_text),
                sanitize_report_text(job_text),
            )
            per_dimension[dimension] = _cosine(candidate_vector, job_vector)
        return per_dimension