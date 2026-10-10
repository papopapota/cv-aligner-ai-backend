from abc import ABC, abstractmethod
from collections.abc import Mapping

from src.domain.compatibility_score import CompatibilityScore


class MatchScorerPort(ABC):
    @abstractmethod
    async def match(
        self,
        candidate_text: str,
        job_text: str,
        candidate_dimensions: Mapping[str, str],
        job_dimensions: Mapping[str, str],
    ) -> CompatibilityScore:
        raise NotImplementedError