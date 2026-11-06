import pytest

from src.domain.tfidf import normalized_tfidf_relevance, tokenize


def test_tokenizes_technical_and_accented_terms() -> None:
    assert tokenize("Python, FastAPI, C++, C#, .NET, Node.js y programación.") == [
        "python",
        "fastapi",
        "c++",
        "c#",
        ".net",
        "node.js",
        "y",
        "programación",
    ]


def test_identical_texts_have_full_relevance() -> None:
    text = "python fastapi postgresql"

    assert normalized_tfidf_relevance(text, text) == pytest.approx(1.0)


def test_disjoint_vocabularies_have_no_relevance() -> None:
    assert normalized_tfidf_relevance("python sql", "java spring") == pytest.approx(
        0.0
    )


def test_an_empty_job_description_has_no_relevance() -> None:
    assert normalized_tfidf_relevance("python", "") == pytest.approx(0.0)


def test_a_job_description_without_valid_tokens_has_no_relevance() -> None:
    assert normalized_tfidf_relevance("python", "!!! ...") == pytest.approx(0.0)


def test_partial_overlap_matches_the_expected_value() -> None:
    expected = 0.5 / (0.5 + (0.5 * (1.0 + 1.0 * 0.4054651081081644)))

    assert normalized_tfidf_relevance(
        "python sql",
        "python java",
    ) == pytest.approx(expected)


def test_relevance_is_zero_when_the_candidate_is_empty() -> None:
    assert normalized_tfidf_relevance("", "python java") == pytest.approx(0.0)
