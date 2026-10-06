from src.application.ports.out.llm_agent_port import AgentRole, LLMAgentPort

_EXTRACTOR_RESPONSE = (
    "EXTRACTED PROFILE: backend engineer with python and fastapi experience."
)
_ANALYZER_RESPONSE = "GAP ANALYSIS: missing kubernetes and postgres depth."
_WRITER_RESPONSE = "OPTIMIZED CV: python backend engineer with fastapi and postgres."
_AUDITOR_RESPONSE = "VARIANCE SCORE: {variance_score}"


class StubLLMAgentAdapter(LLMAgentPort):
    def __init__(
        self,
        variance_score: float = 0.1,
        variance_score_on_first_attempt: float | None = None,
    ) -> None:
        self._variance_score = variance_score
        self._variance_score_on_first_attempt = variance_score_on_first_attempt

    async def complete(self, role: AgentRole, prompt: str) -> str:
        if role is AgentRole.EXTRACTOR:
            return _EXTRACTOR_RESPONSE
        if role is AgentRole.ANALYZER:
            return _ANALYZER_RESPONSE
        if role is AgentRole.WRITER:
            return _WRITER_RESPONSE
        if self._variance_score_on_first_attempt is not None:
            score = self._variance_score_on_first_attempt
            self._variance_score_on_first_attempt = None
        else:
            score = self._variance_score
        return _AUDITOR_RESPONSE.format(variance_score=score)
