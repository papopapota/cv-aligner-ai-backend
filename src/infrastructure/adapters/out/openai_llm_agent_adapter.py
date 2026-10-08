from collections.abc import Mapping

from openai import APIError, AsyncOpenAI

from src.application.ports.out.llm_agent_port import AgentRole, LLMAgentPort

_SYSTEM_PROMPTS: dict[AgentRole, str] = {
    AgentRole.EXTRACTOR: (
        "Extrae el perfil profesional del candidato a partir del CV. "
        "Devuelve un resumen conciso de habilidades, experiencia y logros. "
        "Responde en el mismo idioma del CV."
    ),
    AgentRole.ANALYZER: (
        "Compara el perfil del candidato con la descripción del puesto. "
        "Enumera las carencias más relevantes entre lo que el CV muestra y "
        "lo que el puesto exige. Responde en el mismo idioma de la "
        "descripción del puesto."
    ),
    AgentRole.WRITER: (
        "Reescribe el CV potenciando las aptitudes que cubren cada carencia "
        "del análisis. Mantente fiel a la información original: no inventes "
        "experiencia ni habilidades. Responde en el mismo idioma del CV "
        "original."
    ),
    AgentRole.AUDITOR: (
        "Evalúa cuánto difiere todavía el CV optimizado respecto a la "
        "descripción del puesto. Responde ÚNICAMENTE con un JSON de la forma "
        '{"variance_score": <float 0..1>, "reason": "<texto breve>"}. '
        "Un variance_score alto significa que quedan carencias "
        "significativas."
    ),
}

_TEMPERATURE_BY_ROLE: dict[AgentRole, float] = {
    AgentRole.EXTRACTOR: 0.3,
    AgentRole.ANALYZER: 0.3,
    AgentRole.WRITER: 0.7,
    AgentRole.AUDITOR: 0.0,
}


class LLMError(RuntimeError):
    pass


class OpenAILLMAgentAdapter(LLMAgentPort):
    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        max_tokens: int,
        max_tokens_by_role: Mapping[AgentRole, int],
    ) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens
        self._max_tokens_by_role = max_tokens_by_role

    async def complete(self, role: AgentRole, prompt: str) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPTS[role]},
                    {"role": "user", "content": prompt},
                ],
                temperature=_TEMPERATURE_BY_ROLE[role],
                max_tokens=self._max_tokens_by_role.get(role, self._max_tokens),
            )
        except APIError as exc:
            raise LLMError(
                f"LLM call failed for role '{role.value}' on model "
                f"'{self._model}': {exc}"
            ) from exc

        content = response.choices[0].message.content
        if not content:
            raise LLMError(
                f"LLM returned no content for role '{role.value}' "
                f"on model '{self._model}'."
            )
        return content