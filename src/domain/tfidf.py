import re
from collections import Counter
from math import log

_TOKEN_PATTERN = re.compile(r"[a-z0-9áéíóúüñ+#.]+", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for raw_token in _TOKEN_PATTERN.findall(text.lower()):
        token = raw_token.rstrip(".")
        if token and any(character.isalnum() for character in token):
            tokens.append(token)
    return tokens


def normalized_tfidf_relevance(
    candidate_text: str,
    job_text: str,
) -> float:
    candidate_terms = set(tokenize(candidate_text))
    job_tokens = tokenize(job_text)
    if not job_tokens:
        return 0.0

    job_terms = set(job_tokens)
    corpus = (candidate_terms, job_terms)
    document_frequency: Counter[str] = Counter()
    for document_terms in corpus:
        document_frequency.update(document_terms)

    document_count = len(corpus)
    token_count = len(job_tokens)
    term_frequency = Counter(job_tokens)

    weights: dict[str, float] = {}
    for term in job_terms:
        inverse_document_frequency = (
            log((1 + document_count) / (1 + document_frequency[term])) + 1
        )
        weights[term] = (
            term_frequency[term] / token_count
        ) * inverse_document_frequency

    total_weight = sum(weights.values())
    if total_weight == 0.0:
        return 0.0

    shared_weight = sum(
        weight
        for term, weight in weights.items()
        if term in candidate_terms
    )
    return min(max(shared_weight / total_weight, 0.0), 1.0)
