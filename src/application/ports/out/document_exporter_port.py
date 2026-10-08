from abc import ABC, abstractmethod

from src.domain.optimized_cv import OptimizedCV


class DocumentExporterPort(ABC):
    @abstractmethod
    async def export(self, optimized_cv: OptimizedCV) -> bytes:
        raise NotImplementedError
