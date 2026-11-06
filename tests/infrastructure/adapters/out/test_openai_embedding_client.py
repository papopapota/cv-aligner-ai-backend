from typing import cast

import httpx2
import pytest
from openai import APIError, AsyncOpenAI

from src.infrastructure.adapters.out.openai_embedding_client import (
    EmbeddingClientError,
    OpenAIEmbeddingClient,
)


class _FakeEmbedding:
    def __init__(self, index: int, embedding: list[float]) -> None:
        self.index = index
        self.embedding = embedding


class _FakeEmbeddingsResponse:
    def __init__(self, data: list[_FakeEmbedding]) -> None:
        self.data = data


class _FakeEmbeddings:
    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self._vectors = vectors
        self.calls: list[tuple[str, list[str]]] = []

    async def create(
        self,
        model: str,
        input: list[str],
    ) -> _FakeEmbeddingsResponse:
        self.calls.append((model, list(input)))
        data = [
            _FakeEmbedding(i, self._vectors.get(text, [0.0, 0.0]))
            for i, text in enumerate(input)
        ]
        return _FakeEmbeddingsResponse(data)


class _FakeClient:
    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self.embeddings = _FakeEmbeddings(vectors)


def _client(
    vectors: dict[str, list[float]],
) -> tuple[OpenAIEmbeddingClient, _FakeEmbeddings]:
    fake = _FakeClient(vectors)
    return (
        OpenAIEmbeddingClient(
            client=cast(AsyncOpenAI, fake),
            model="embedding-model",
        ),
        fake.embeddings,
    )


async def test_returns_embeddings_in_input_order() -> None:
    client, _ = _client(
        {
            "first": [1.0, 0.0],
            "second": [0.0, 1.0],
        }
    )

    assert await client.embed(["second", "first"]) == [
        [0.0, 1.0],
        [1.0, 0.0],
    ]


async def test_uses_the_configured_model() -> None:
    client, embeddings = _client({"alpha": [1.0, 0.0]})

    await client.embed(["alpha"])

    assert embeddings.calls == [("embedding-model", ["alpha"])]


async def test_does_not_call_the_api_for_empty_input() -> None:
    client, embeddings = _client({})

    assert await client.embed([]) == []
    assert embeddings.calls == []


async def test_wraps_api_errors() -> None:
    class _FailingEmbeddings(_FakeEmbeddings):
        async def create(
            self,
            model: str,
            input: list[str],
        ) -> _FakeEmbeddingsResponse:
            raise APIError(
                "boom",
                request=httpx2.Request(method="POST", url="http://example.test"),
                body=None,
            )

    class _FailingClient:
        embeddings = _FailingEmbeddings(vectors={})

    client = OpenAIEmbeddingClient(
        client=cast(AsyncOpenAI, _FailingClient()),
        model="embedding-model",
    )

    with pytest.raises(EmbeddingClientError):
        await client.embed(["alpha"])
