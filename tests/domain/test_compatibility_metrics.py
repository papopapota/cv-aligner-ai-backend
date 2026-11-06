import math

import pytest

from src.domain.compatibility_metrics import (
    CompatibilityWeights,
    compatibility_index,
    normalized_cosine,
    normalized_euclidean,
)


def test_normalized_cosine_of_identical_vectors_is_one() -> None:
    assert normalized_cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)


def test_normalized_cosine_of_orthogonal_vectors_is_zero() -> None:
    assert normalized_cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_normalized_cosine_clamps_opposite_vectors_to_zero() -> None:
    assert normalized_cosine([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(0.0)


def test_normalized_cosine_with_a_zero_vector_is_zero() -> None:
    assert normalized_cosine([0.0, 0.0], [1.0, 0.0]) == pytest.approx(0.0)


def test_normalized_cosine_rejects_different_dimensions() -> None:
    with pytest.raises(ValueError):
        normalized_cosine([1.0], [1.0, 0.0])


def test_normalized_euclidean_of_identical_vectors_is_one() -> None:
    assert normalized_euclidean([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)


def test_normalized_euclidean_of_opposite_vectors_is_zero() -> None:
    assert normalized_euclidean([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(0.0)


def test_normalized_euclidean_with_a_known_distance() -> None:
    expected = 1.0 - math.sqrt(2.0) / 2.0

    assert normalized_euclidean([1.0, 0.0], [0.0, 1.0]) == pytest.approx(
        expected
    )


def test_normalized_euclidean_with_a_zero_vector_is_zero() -> None:
    assert normalized_euclidean([0.0, 0.0], [1.0, 0.0]) == pytest.approx(0.0)


def test_normalized_euclidean_rejects_a_non_positive_dmax() -> None:
    with pytest.raises(ValueError):
        normalized_euclidean([1.0, 0.0], [1.0, 0.0], dmax=0.0)


def test_compatibility_index_with_all_components_at_one_is_one_hundred() -> None:
    assert compatibility_index(1.0, 1.0, 1.0) == pytest.approx(100.0)


def test_compatibility_index_with_all_components_at_zero_is_zero() -> None:
    assert compatibility_index(0.0, 0.0, 0.0) == pytest.approx(0.0)


def test_compatibility_index_with_a_known_mix() -> None:
    assert compatibility_index(0.5, 0.5, 0.5) == pytest.approx(50.0)


def test_compatibility_index_uses_the_default_weights() -> None:
    expected = 100.0 * ((0.50 * 0.8) + (0.30 * 0.4) + (0.20 * 0.2))

    assert compatibility_index(0.8, 0.4, 0.2) == pytest.approx(expected)


def test_compatibility_index_accepts_custom_weights() -> None:
    weights = CompatibilityWeights(ncos=0.2, ntfidf=0.3, neuc=0.5)

    assert compatibility_index(1.0, 1.0, 1.0, weights) == pytest.approx(100.0)


def test_compatibility_index_clamps_out_of_range_components() -> None:
    assert compatibility_index(1.5, -0.5, 2.0) == pytest.approx(70.0)


def test_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError):
        CompatibilityWeights(ncos=0.5, ntfidf=0.5, neuc=0.5)


@pytest.mark.parametrize(
    ("ncos", "ntfidf", "neuc"),
    [
        (1.1, -0.1, 0.0),
        (-0.1, 0.6, 0.5),
        (1.2, 0.0, -0.2),
    ],
)
def test_weights_must_be_between_zero_and_one(
    ncos: float,
    ntfidf: float,
    neuc: float,
) -> None:
    with pytest.raises(ValueError):
        CompatibilityWeights(ncos=ncos, ntfidf=ntfidf, neuc=neuc)
