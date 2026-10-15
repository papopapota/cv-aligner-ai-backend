import json
import logging
import re

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.application.ports.out.llm_agent_port import AgentRole, LLMAgentPort
from src.application.ports.out.workflow_orchestrator_port import (
    WorkflowOrchestratorPort,
)
from src.domain.audit_rules import (
    MAX_VARIANCE_THRESHOLD,
    MAX_WRITER_ATTEMPTS,
    AuditDecision,
    evaluate_variance,
)
from src.domain.candidate_cv import CandidateCV
from src.domain.errors import InvalidUploadError
from src.domain.job_description import JobDescription
from src.domain.optimized_cv import OptimizedCV
from src.domain.shared_state import SharedState

logger = logging.getLogger(__name__)

_RETRY = "retry"
_APPROVE = "approve"
_JSON_OBJECT_PATTERN = re.compile(r"\{[^{}]*\}")


def parse_variance_score(audit: str) -> float:
    structured = _extract_variance_score_from_json(audit)
    if structured is not None:
        return structured
    for token in audit.replace(",", ".").split():
        try:
            return float(token)
        except ValueError:
            continue
    raise InvalidUploadError(
        "The auditor did not return a numeric variance score."
    )


def parse_audit_reason(audit: str) -> str:
    payload = _extract_json_payload(audit)
    if payload is not None:
        reason = payload.get("reason")
        if isinstance(reason, str):
            return reason
    return audit.strip()


def _extract_variance_score_from_json(audit: str) -> float | None:
    payload = _extract_json_payload(audit)
    if payload is None:
        return None
    value = payload.get("variance_score")
    if not isinstance(value, (int, float, str)):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _extract_json_payload(audit: str) -> dict[str, object] | None:
    match = _JSON_OBJECT_PATTERN.search(audit)
    if match is None:
        return None
    try:
        payload = json.loads(match.group(0))
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


class LangGraphOrchestratorAdapter(WorkflowOrchestratorPort):
    def __init__(
        self,
        llm_agent: LLMAgentPort,
        variance_threshold: float = MAX_VARIANCE_THRESHOLD,
    ) -> None:
        self._llm_agent = llm_agent
        self._variance_threshold = variance_threshold
        self._graph: CompiledStateGraph[SharedState] = self._build_graph()

    async def optimize(
        self,
        candidate: CandidateCV,
        job_description: JobDescription,
    ) -> OptimizedCV:
        final_state = await self._graph.ainvoke(
            SharedState(
                candidate_cv_text=candidate.raw_text,
                job_description_text=job_description.raw_text,
            )
        )

        optimized = OptimizedCV(
            content=final_state["optimized_text"],
            variance_score=final_state["variance_score"],
            writer_attempts=final_state["writer_attempts"],
            variance_threshold=self._variance_threshold,
        )
        logger.info(
            "CV optimization finished: variance=%s attempts=%s "
            "within_threshold=%s",
            optimized.variance_score,
            optimized.writer_attempts,
            optimized.is_within_threshold(),
        )
        return optimized

    def _build_graph(self) -> CompiledStateGraph[SharedState]:
        graph: StateGraph[SharedState] = StateGraph(SharedState)
        graph.add_node("extractor", self._extractor)
        graph.add_node("analyzer", self._analyzer)
        graph.add_node("writer", self._writer)
        graph.add_node("auditor", self._auditor)

        graph.add_edge(START, "extractor")
        graph.add_edge("extractor", "analyzer")
        graph.add_edge("analyzer", "writer")
        graph.add_edge("writer", "auditor")
        graph.add_conditional_edges(
            "auditor",
            self._route_after_audit,
            {_RETRY: "writer", _APPROVE: END},
        )

        return graph.compile()

    async def _extractor(self, state: SharedState) -> dict[str, object]:
        profile = await self._llm_agent.complete(
            AgentRole.EXTRACTOR,
            f"Candidate CV:\n{state.candidate_cv_text}",
        )
        return {"extracted_profile": profile}

    async def _analyzer(self, state: SharedState) -> dict[str, object]:
        analysis = await self._llm_agent.complete(
            AgentRole.ANALYZER,
            f"Job description:\n{state.job_description_text}\n"
            f"Profile:\n{state.extracted_profile}",
        )
        return {"gap_analysis": analysis}

    async def _writer(self, state: SharedState) -> dict[str, object]:
        prompt = self._writer_prompt(state)
        optimized_text = await self._llm_agent.complete(
            AgentRole.WRITER,
            prompt,
        )
        return {
            "optimized_text": optimized_text,
            "writer_attempts": state.writer_attempts + 1,
        }

    def _writer_prompt(self, state: SharedState) -> str:
        if not state.optimized_text:
            return (
                f"Job description:\n{state.job_description_text}\n"
                f"Gaps:\n{state.gap_analysis}\n"
                f"CV:\n{state.candidate_cv_text}"
            )
        return (
            f"Job description:\n{state.job_description_text}\n"
            f"Gaps:\n{state.gap_analysis}\n"
            f"Previous optimized CV:\n{state.optimized_text}\n"
            f"Auditor feedback (variance {state.variance_score}):\n"
            f"{state.audit_reason}\n"
            "Corrige específicamente las carencias señaladas por el auditor "
            "en el CV optimizado anterior, sin inventar experiencia ni "
            "habilidades.\n"
            f"Original CV:\n{state.candidate_cv_text}"
        )

    async def _auditor(self, state: SharedState) -> dict[str, object]:
        audit = await self._llm_agent.complete(
            AgentRole.AUDITOR,
            f"Job description:\n{state.job_description_text}\n"
            f"Gaps:\n{state.gap_analysis}\n"
            f"Optimized CV:\n{state.optimized_text}",
        )
        variance_score = parse_variance_score(audit)
        logger.info(
            "Auditor attempt %s: variance=%s reason=%s",
            state.writer_attempts,
            variance_score,
            parse_audit_reason(audit),
        )
        return {
            "variance_score": variance_score,
            "audit_reason": parse_audit_reason(audit),
        }

    def _route_after_audit(self, state: SharedState) -> str:
        decision = evaluate_variance(
            state.variance_score,
            self._variance_threshold,
        )
        if (
            decision is AuditDecision.RETRY
            and state.writer_attempts < MAX_WRITER_ATTEMPTS
        ):
            logger.warning(
                "Variance %s above threshold %s after attempt %s: retrying "
                "the writer.",
                state.variance_score,
                self._variance_threshold,
                state.writer_attempts,
            )
            return _RETRY
        return _APPROVE
