import json
import re

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.application.ports.out.llm_agent_port import AgentRole, LLMAgentPort
from src.application.ports.out.match_scorer_port import MatchScorerPort
from src.application.ports.out.workflow_orchestrator_port import (
    WorkflowOrchestratorPort,
)
from src.domain.audit_rules import (
    DEFAULT_R_TOTAL_TARGET,
    MAX_WRITER_ATTEMPTS,
    AuditDecision,
    evaluate_variance,
)
from src.domain.candidate_cv import CandidateCV
from src.domain.compatibility_score import CompatibilityScore
from src.domain.errors import InvalidUploadError
from src.domain.job_description import JobDescription
from src.domain.optimized_cv import OptimizedCV
from src.domain.semantic_profile import SemanticProfile
from src.domain.shared_state import SharedState

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


def _extract_variance_score_from_json(audit: str) -> float | None:
    match = _JSON_OBJECT_PATTERN.search(audit)
    if match is None:
        return None
    try:
        payload = json.loads(match.group(0))
        return float(payload["variance_score"])
    except (KeyError, TypeError, ValueError):
        return None


def parse_semantic_profile(text: str) -> SemanticProfile:
    profile = _extract_semantic_profile_from_json(text)
    if profile is None:
        raise InvalidUploadError(
            "The extractor did not return a valid JSON semantic profile."
        )
    return profile


def _extract_semantic_profile_from_json(text: str) -> SemanticProfile | None:
    match = _JSON_OBJECT_PATTERN.search(text)
    if match is None:
        return None
    try:
        payload = json.loads(match.group(0))
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    profile = SemanticProfile(
        summary=_as_text(payload.get("summary")),
        technical_skills=_as_text(payload.get("technical_skills")),
        experience=_as_text(payload.get("experience")),
        education=_as_text(payload.get("education")),
        certifications=_as_text(payload.get("certifications")),
        languages=_as_text(payload.get("languages")),
    )
    if not (profile.summary.strip() or profile.as_dimensions()):
        return None
    return profile


def _as_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def _build_analyzer_prompt(
    state: SharedState,
    baseline_match: CompatibilityScore,
) -> str:
    scorecard = "\n".join(
        f"- {dimension}: {score:.3f}"
        for dimension, score in sorted(baseline_match.per_dimension.items())
    )
    return (
        f"Job description:\n{state.job_description_text}\n"
        f"Profile:\n{state.extracted_profile}\n"
        f"Baseline match (R_total={baseline_match.r_total:.3f}):\n"
        f"{scorecard}\n"
        "Prioriza cerrar las brechas en las dimensiones con menor similitud."
    )


class LangGraphOrchestratorAdapter(WorkflowOrchestratorPort):
    def __init__(
        self,
        llm_agent: LLMAgentPort,
        match_scorer: MatchScorerPort | None = None,
        r_total_target: float = DEFAULT_R_TOTAL_TARGET,
    ) -> None:
        self._llm_agent = llm_agent
        self._match_scorer = match_scorer
        self._r_total_target = r_total_target
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

        if final_state["best_text"]:
            return OptimizedCV(
                content=final_state["best_text"],
                variance_score=final_state["best_variance"],
                writer_attempts=final_state["writer_attempts"],
                r_total=final_state["best_r_total"],
                per_dimension=final_state["best_per_dimension"],
                gap_report=final_state["gap_analysis"],
            )

        return OptimizedCV(
            content=final_state["optimized_text"],
            variance_score=final_state["variance_score"],
            writer_attempts=final_state["writer_attempts"],
            gap_report=final_state["gap_analysis"],
        )

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
        if self._match_scorer is None:
            return {"extracted_profile": profile}
        return {
            "extracted_profile": profile,
            "candidate_profile": parse_semantic_profile(profile),
        }

    async def _analyzer(self, state: SharedState) -> dict[str, object]:
        if self._match_scorer is None:
            analysis = await self._llm_agent.complete(
                AgentRole.ANALYZER,
                f"Job description:\n{state.job_description_text}\n"
                f"Profile:\n{state.extracted_profile}",
            )
            return {"gap_analysis": analysis}

        job_profile = parse_semantic_profile(
            await self._llm_agent.complete(
                AgentRole.EXTRACTOR,
                f"Job description:\n{state.job_description_text}",
            )
        )
        baseline_match = await self._match_scorer.match(
            candidate_text=state.candidate_cv_text,
            job_text=state.job_description_text,
            candidate_dimensions=state.candidate_profile.as_dimensions()
            if state.candidate_profile is not None
            else {},
            job_dimensions=job_profile.as_dimensions(),
        )
        analysis = await self._llm_agent.complete(
            AgentRole.ANALYZER,
            _build_analyzer_prompt(state, baseline_match),
        )
        return {
            "gap_analysis": analysis,
            "job_profile": job_profile,
            "baseline_match": baseline_match,
        }

    async def _writer(self, state: SharedState) -> dict[str, object]:
        optimized_text = await self._llm_agent.complete(
            AgentRole.WRITER,
            f"Job description:\n{state.job_description_text}\n"
            f"Gaps:\n{state.gap_analysis}\n"
            f"CV:\n{state.candidate_cv_text}",
        )
        return {
            "optimized_text": optimized_text,
            "writer_attempts": state.writer_attempts + 1,
        }

    async def _auditor(self, state: SharedState) -> dict[str, object]:
        audit = await self._llm_agent.complete(
            AgentRole.AUDITOR,
            f"Job description:\n{state.job_description_text}\n"
            f"Gaps:\n{state.gap_analysis}\n"
            f"Optimized CV:\n{state.optimized_text}",
        )
        variance_score = parse_variance_score(audit)
        if self._match_scorer is None:
            return {"variance_score": variance_score}

        candidate_profile = parse_semantic_profile(
            await self._llm_agent.complete(
                AgentRole.EXTRACTOR,
                f"Optimized CV:\n{state.optimized_text}",
            )
        )
        optimized_match = await self._match_scorer.match(
            candidate_text=state.optimized_text,
            job_text=state.job_description_text,
            candidate_dimensions=candidate_profile.as_dimensions(),
            job_dimensions=state.job_profile.as_dimensions()
            if state.job_profile is not None
            else {},
        )
        updates: dict[str, object] = {
            "variance_score": variance_score,
            "optimized_match": optimized_match,
        }
        if state.best_text == "" or optimized_match.r_total > state.best_r_total:
            updates["best_text"] = state.optimized_text
            updates["best_r_total"] = optimized_match.r_total
            updates["best_variance"] = variance_score
            updates["best_per_dimension"] = optimized_match.per_dimension
        return updates

    def _route_after_audit(self, state: SharedState) -> str:
        decision = evaluate_variance(state.variance_score)
        match_approved = (
            self._match_scorer is None
            or (
                state.optimized_match is not None
                and state.optimized_match.r_total >= self._r_total_target
            )
        )
        if (
            (decision is AuditDecision.RETRY or not match_approved)
            and state.writer_attempts < MAX_WRITER_ATTEMPTS
        ):
            return _RETRY
        return _APPROVE
