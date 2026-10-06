from langgraph.graph import END, START, StateGraph

from src.application.ports.out.llm_agent_port import AgentRole, LLMAgentPort
from src.application.ports.out.workflow_orchestrator_port import (
    WorkflowOrchestratorPort,
)
from src.domain.audit_rules import (
    MAX_WRITER_ATTEMPTS,
    AuditDecision,
    evaluate_variance,
)
from src.domain.candidate_cv import CandidateCV
from src.domain.errors import InvalidUploadError
from src.domain.job_description import JobDescription
from src.domain.optimized_cv import OptimizedCV
from src.domain.shared_state import SharedState

_RETRY = "retry"
_APPROVE = "approve"


class LangGraphOrchestratorAdapter(WorkflowOrchestratorPort):
    def __init__(self, llm_agent: LLMAgentPort) -> None:
        self._llm_agent = llm_agent
        self._graph = self._build_graph()

    async def optimize(
        self,
        candidate: CandidateCV,
        job_description: JobDescription,
    ) -> OptimizedCV:
        final_state = await self._graph.ainvoke(
            {
                "candidate_cv_text": candidate.raw_text,
                "job_description_text": job_description.raw_text,
            }
        )

        return OptimizedCV(
            content=final_state["optimized_text"],
            variance_score=final_state["variance_score"],
            writer_attempts=final_state["writer_attempts"],
        )

    def _build_graph(self):
        graph = StateGraph(SharedState)
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

    async def _extractor(self, state: SharedState) -> dict:
        profile = await self._llm_agent.complete(
            AgentRole.EXTRACTOR,
            f"Candidate CV:\n{state.candidate_cv_text}",
        )
        return {"extracted_profile": profile}

    async def _analyzer(self, state: SharedState) -> dict:
        analysis = await self._llm_agent.complete(
            AgentRole.ANALYZER,
            f"Job description:\n{state.job_description_text}\n"
            f"Profile:\n{state.extracted_profile}",
        )
        return {"gap_analysis": analysis}

    async def _writer(self, state: SharedState) -> dict:
        optimized_text = await self._llm_agent.complete(
            AgentRole.WRITER,
            f"Gaps:\n{state.gap_analysis}\nCV:\n{state.candidate_cv_text}",
        )
        return {
            "optimized_text": optimized_text,
            "writer_attempts": state.writer_attempts + 1,
        }

    async def _auditor(self, state: SharedState) -> dict:
        audit = await self._llm_agent.complete(
            AgentRole.AUDITOR,
            f"Optimized CV:\n{state.optimized_text}",
        )
        return {"variance_score": self._parse_variance_score(audit)}

    def _route_after_audit(self, state: SharedState) -> str:
        decision = evaluate_variance(state.variance_score)
        if (
            decision is AuditDecision.RETRY
            and state.writer_attempts < MAX_WRITER_ATTEMPTS
        ):
            return _RETRY
        return _APPROVE

    def _parse_variance_score(self, audit: str) -> float:
        for token in audit.replace(",", ".").split():
            try:
                return float(token)
            except ValueError:
                continue
        raise InvalidUploadError(
            "The auditor did not return a numeric variance score."
        )
