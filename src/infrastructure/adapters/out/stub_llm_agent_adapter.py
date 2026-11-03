from src.application.ports.out.llm_agent_port import AgentRole, LLMAgentPort

_EXTRACTOR_RESPONSE = (
    '{"summary": "EXTRACTED PROFILE: backend engineer with python and fastapi '
    'experience.", "technical_skills": "python, fastapi", "experience": '
    '"backend engineering", "education": "", "certifications": "", '
    '"languages": ""}'
)
_ANALYZER_RESPONSE = "GAP ANALYSIS: missing kubernetes and postgres depth."
_WRITER_RESPONSE = "OPTIMIZED CV: python backend engineer with fastapi and postgres."
_AUDITOR_RESPONSE = "VARIANCE SCORE: {variance_score}"


class StubLLMAgentAdapter(LLMAgentPort):
    def __init__(
        self,
        variance_score: float = 0.1,
        variance_score_on_first_attempt: float | None = None,
        writer_outputs: list[str] | None = None,
        original_variance_score: float = 0.8,
    ) -> None:
        self._variance_score = variance_score
        self._variance_score_on_first_attempt = variance_score_on_first_attempt
        self._writer_outputs = list(writer_outputs) if writer_outputs else None
        self._original_variance_score = original_variance_score

    async def complete(self, role: AgentRole, prompt: str) -> str:
        if role is AgentRole.EXTRACTOR:
            return _EXTRACTOR_RESPONSE
        if role is AgentRole.ANALYZER:
            return _ANALYZER_RESPONSE
        if role is AgentRole.WRITER:
            if self._writer_outputs:
                return self._writer_outputs.pop(0)
            return _WRITER_RESPONSE
        if "Original CV:" in prompt:
            return _AUDITOR_RESPONSE.format(
                variance_score=self._original_variance_score
            )
        if self._variance_score_on_first_attempt is not None:
            score = self._variance_score_on_first_attempt
            self._variance_score_on_first_attempt = None
        else:
            score = self._variance_score
        return _AUDITOR_RESPONSE.format(variance_score=score)
