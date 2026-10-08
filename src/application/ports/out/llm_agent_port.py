from abc import ABC, abstractmethod
from enum import Enum


class AgentRole(Enum):
    EXTRACTOR = "extractor"
    ANALYZER = "analyzer"
    WRITER = "writer"
    AUDITOR = "auditor"


class LLMAgentPort(ABC):
    @abstractmethod
    async def complete(self, role: AgentRole, prompt: str) -> str:
        raise NotImplementedError
