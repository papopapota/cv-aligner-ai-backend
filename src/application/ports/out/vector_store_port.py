from abc import ABC, abstractmethod


class VectorStorePort(ABC):
    @abstractmethod
    async def upsert(self, documents: list[str]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def retrieve(self, query: str, limit: int) -> list[str]:
        raise NotImplementedError
