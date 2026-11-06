from collections.abc import Sequence
from typing import Protocol

from openai import APIError, AsyncOpenAI


class EmbeddingClient(Protocol):
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        ...


class EmbeddingClientError(RuntimeError):
    pass


class OpenAIEmbeddingClient:
    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = await self._client.embeddings.create(
                model=self._model,
                input=list(texts),
            )
        except APIError as exc:
            raise EmbeddingClientError(
                f"Embedding call failed on model '{self._model}': {exc}"
            ) from exc
        ordered = sorted(response.data, key=lambda item: item.index)
        return [list(item.embedding) for item in ordered]
