from abc import ABC, abstractmethod


class CVParserPort(ABC):
    @abstractmethod
    async def parse(self, filename: str, content: bytes) -> str:
        raise NotImplementedError