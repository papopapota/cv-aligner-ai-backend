from collections.abc import Mapping

import pytest

from src.application.ports.out.llm_agent_port import AgentRole
from src.application.ports.out.match_scorer_port import MatchScorerPort
from src.domain.audit_rules import MAX_WRITER_ATTEMPTS
from src.domain.candidate_cv import CandidateCV
from src.domain.compatibility_score import CompatibilityScore
from src.domain.errors import InvalidUploadError
from src.domain.job_description import JobDescription
from src.domain.semantic_profile import SemanticProfile
from src.domain.shared_state import SharedState
from src.domain.uploaded_file_metadata import UploadedFileMetadata
from src.infrastructure.adapters.out.langgraph_orchestrator_adapter import (
    LangGraphOrchestratorAdapter,
    parse_semantic_profile,
    parse_variance_score,
)
from src.infrastructure.adapters.out.stub_llm_agent_adapter import (
    StubLLMAgentAdapter,
)

_CV_TEXT = "Python backend engineer with fastapi."
_JOB_TEXT = "Looking for a FastAPI developer."
_GAP_TEXT = "GAP ANALYSIS: missing kubernetes and postgres depth."


def _candidate() -> CandidateCV:
    return CandidateCV(
        metadata=UploadedFileMetadata.from_bytes(
            "cv.pdf",
            "application/pdf",
            b"%PDF-1.7 fake",
        ),
        raw_text=_CV_TEXT,
    )


def _job_description() -> JobDescription:
    return JobDescription(
        metadata=UploadedFileMetadata.from_job_description_bytes(
            "job.txt",
            "text/plain",
            b"fake spec",
        ),
        raw_text=_JOB_TEXT,
    )


def _orchestrator(
    variance_score: float = 0.1,
    variance_score_on_first_attempt: float | None = None,
) -> LangGraphOrchestratorAdapter:
    return LangGraphOrchestratorAdapter(
        StubLLMAgentAdapter(
            variance_score=variance_score,
            variance_score_on_first_attempt=variance_score_on_first_attempt,
        )
    )


def _score(
    r_total: float,
    per_dimension: dict[str, float] | None = None,
) -> CompatibilityScore:
    return CompatibilityScore(
        s_cosine=r_total,
        d_euclidean=0.0,
        a_contextual=0.0,
        r_total=r_total,
        per_dimension=per_dimension or {},
    )


class _FakeMatchScorer(MatchScorerPort):
    def __init__(self, scores: list[CompatibilityScore]) -> None:
        self._scores = list(scores)
        self.calls: list[tuple[str, str, Mapping[str, str], Mapping[str, str]]] = []

    async def match(
        self,
        candidate_text: str,
        job_text: str,
        candidate_dimensions: Mapping[str, str],
        job_dimensions: Mapping[str, str],
    ) -> CompatibilityScore:
        self.calls.append(
            (candidate_text, job_text, candidate_dimensions, job_dimensions)
        )
        if len(self._scores) > 1:
            return self._scores.pop(0)
        return self._scores[0]


async def test_runs_the_whole_graph_and_approves_a_low_variance() -> None:
    optimized = await _orchestrator(variance_score=0.1).optimize(
        _candidate(),
        _job_description(),
    )

    assert optimized.variance_score == 0.1
    assert optimized.writer_attempts == 1
    assert optimized.is_within_threshold()
    assert optimized.content
    assert optimized.r_total is None
    assert optimized.per_dimension == {}
    assert optimized.gap_report == _GAP_TEXT


async def test_retries_the_writer_once_when_the_variance_is_high() -> None:
    optimized = await _orchestrator(
        variance_score=0.1,
        variance_score_on_first_attempt=0.9,
    ).optimize(_candidate(), _job_description())

    assert optimized.writer_attempts == 2
    assert optimized.variance_score == 0.1


async def test_stops_retrying_at_the_attempt_cap() -> None:
    optimized = await _orchestrator(variance_score=0.9).optimize(
        _candidate(),
        _job_description(),
    )

    assert optimized.writer_attempts == MAX_WRITER_ATTEMPTS
    assert not optimized.is_within_threshold()


async def test_runs_the_nodes_in_order() -> None:
    prompts: list[str] = []

    class _Recorder(StubLLMAgentAdapter):
        async def complete(self, role: AgentRole, prompt: str) -> str:
            prompts.append(prompt)
            return await super().complete(role, prompt)

    orchestrator = LangGraphOrchestratorAdapter(_Recorder(variance_score=0.1))

    await orchestrator.optimize(_candidate(), _job_description())

    assert len(prompts) == 4
    assert _CV_TEXT in prompts[0]
    assert _JOB_TEXT in prompts[1]
    assert _JOB_TEXT in prompts[2]
    assert _JOB_TEXT in prompts[3]
    assert _GAP_TEXT in prompts[3]


async def test_rejects_an_audit_without_a_numeric_score() -> None:
    class _NoScore(StubLLMAgentAdapter):
        async def complete(self, role: AgentRole, prompt: str) -> str:
            if role is AgentRole.AUDITOR:
                return "I cannot tell"
            return await super().complete(role, prompt)

    orchestrator = LangGraphOrchestratorAdapter(_NoScore(variance_score=0.1))

    with pytest.raises(InvalidUploadError):
        await orchestrator.optimize(_candidate(), _job_description())


def test_parses_a_pure_json_audit() -> None:
    assert parse_variance_score('{"variance_score": 0.4, "reason": "ok"}') == 0.4


def test_parses_a_json_audit_wrapped_in_markdown_fences() -> None:
    audit = '```json\n{"variance_score": 0.2, "reason": "close enough"}\n```'

    assert parse_variance_score(audit) == 0.2


def test_falls_back_to_a_free_float_when_there_is_no_json() -> None:
    assert parse_variance_score("Variance below 0.20") == 0.2


def test_parses_a_integer_score_in_json() -> None:
    assert parse_variance_score('{"variance_score": 1}') == 1.0


def test_rejects_an_audit_without_any_numeric_score() -> None:
    with pytest.raises(InvalidUploadError):
        parse_variance_score("I cannot tell")


def test_parses_a_full_semantic_profile() -> None:
    extractor_output = (
        '{"summary": "Backend engineer", "technical_skills": "python", '
        '"experience": "3 years", "education": "CS degree", '
        '"certifications": "AWS", "languages": "english"}'
    )

    profile = parse_semantic_profile(extractor_output)

    assert profile == SemanticProfile(
        summary="Backend engineer",
        technical_skills="python",
        experience="3 years",
        education="CS degree",
        certifications="AWS",
        languages="english",
    )
    assert profile.as_dimensions() == {
        "technical_skills": "python",
        "experience": "3 years",
        "education": "CS degree",
        "certifications": "AWS",
        "languages": "english",
    }


def test_parses_a_profile_wrapped_in_markdown_fences() -> None:
    extractor_output = (
        '```json\n{"summary": "Engineer", "technical_skills": "fastapi", '
        '"experience": "1 year"}\n```'
    )

    profile = parse_semantic_profile(extractor_output)

    assert profile.summary == "Engineer"
    assert profile.as_dimensions() == {
        "technical_skills": "fastapi",
        "experience": "1 year",
    }


def test_defaults_missing_dimensions_to_empty_strings() -> None:
    profile = parse_semantic_profile('{"summary": "Engineer"}')

    assert profile.summary == "Engineer"
    assert profile.as_dimensions() == {}


def test_normalizes_a_non_string_dimension_to_text() -> None:
    extractor_output = '{"summary": "Engineer", "technical_skills": ["python", "go"]}'

    profile = parse_semantic_profile(extractor_output)

    assert profile.technical_skills == "python; go"


def test_ignores_unknown_keys() -> None:
    extractor_output = (
        '{"summary": "Engineer", "technical_skills": "python", '
        '"favorite_color": "blue"}'
    )

    profile = parse_semantic_profile(extractor_output)

    assert profile.technical_skills == "python"


def test_rejects_text_without_any_usable_profile() -> None:
    with pytest.raises(InvalidUploadError):
        parse_semantic_profile("I cannot extract a profile")


async def test_approves_when_variance_and_r_total_meet_the_targets() -> None:
    scorer = _FakeMatchScorer([_score(0.9), _score(0.9)])
    orchestrator = LangGraphOrchestratorAdapter(
        StubLLMAgentAdapter(variance_score=0.1),
        match_scorer=scorer,
    )

    optimized = await orchestrator.optimize(_candidate(), _job_description())

    assert optimized.writer_attempts == 1
    assert optimized.variance_score == 0.1
    assert optimized.is_within_threshold()
    assert len(scorer.calls) == 2
    assert scorer.calls[0][0] == _CV_TEXT
    assert scorer.calls[1][0] == optimized.content
    assert scorer.calls[0][2] == {
        "technical_skills": "python, fastapi",
        "experience": "backend engineering",
    }


async def test_retries_when_the_r_total_is_below_the_target() -> None:
    scorer = _FakeMatchScorer([_score(0.9), _score(0.5), _score(0.5), _score(0.5)])
    orchestrator = LangGraphOrchestratorAdapter(
        StubLLMAgentAdapter(variance_score=0.1),
        match_scorer=scorer,
    )

    optimized = await orchestrator.optimize(_candidate(), _job_description())

    assert optimized.writer_attempts == MAX_WRITER_ATTEMPTS
    assert len(scorer.calls) == 1 + MAX_WRITER_ATTEMPTS


async def test_respects_a_custom_r_total_target() -> None:
    scorer = _FakeMatchScorer([_score(0.9), _score(0.84)])
    orchestrator = LangGraphOrchestratorAdapter(
        StubLLMAgentAdapter(variance_score=0.1),
        match_scorer=scorer,
        r_total_target=0.80,
    )

    optimized = await orchestrator.optimize(_candidate(), _job_description())

    assert optimized.writer_attempts == 1


async def test_retries_when_the_variance_is_high_with_scoring_enabled() -> None:
    scorer = _FakeMatchScorer(
        [_score(0.9), _score(0.9), _score(0.9), _score(0.9)]
    )
    orchestrator = LangGraphOrchestratorAdapter(
        StubLLMAgentAdapter(variance_score=0.9),
        match_scorer=scorer,
    )

    optimized = await orchestrator.optimize(_candidate(), _job_description())

    assert optimized.writer_attempts == MAX_WRITER_ATTEMPTS
    assert not optimized.is_within_threshold()


async def test_feeds_the_analyzer_with_the_baseline_scorecard() -> None:
    prompts: list[str] = []

    class _Recorder(StubLLMAgentAdapter):
        async def complete(self, role: AgentRole, prompt: str) -> str:
            prompts.append(prompt)
            return await super().complete(role, prompt)

    scorer = _FakeMatchScorer(
        [_score(0.9, per_dimension={"technical_skills": 0.42}), _score(0.9)]
    )
    orchestrator = LangGraphOrchestratorAdapter(
        _Recorder(variance_score=0.1),
        match_scorer=scorer,
    )

    await orchestrator.optimize(_candidate(), _job_description())

    analysis_prompt = prompts[2]
    assert "Baseline match (R_total=" in analysis_prompt
    assert "technical_skills: 0.420" in analysis_prompt
    assert "Prioriza cerrar las brechas" in analysis_prompt


async def test_extracts_the_job_profile_with_an_extra_explorer_call() -> None:
    prompts: list[str] = []

    class _Recorder(StubLLMAgentAdapter):
        async def complete(self, role: AgentRole, prompt: str) -> str:
            prompts.append(prompt)
            return await super().complete(role, prompt)

    scorer = _FakeMatchScorer([_score(0.9), _score(0.9)])
    orchestrator = LangGraphOrchestratorAdapter(
        _Recorder(variance_score=0.1),
        match_scorer=scorer,
    )

    await orchestrator.optimize(_candidate(), _job_description())

    assert len(prompts) == 6
    assert "Job description" in prompts[1]
    assert "Optimized CV" in prompts[4]
    assert scorer.calls[0][3] == {
        "technical_skills": "python, fastapi",
        "experience": "backend engineering",
    }


async def test_tracks_the_best_version_while_retrying() -> None:
    scorer = _FakeMatchScorer([_score(0.9), _score(0.7), _score(0.9), _score(0.6)])
    stub = StubLLMAgentAdapter(
        variance_score=0.9,
        writer_outputs=["first version", "second version", "third version"],
    )
    orchestrator = LangGraphOrchestratorAdapter(stub, match_scorer=scorer)

    state = await orchestrator._graph.ainvoke(  # noqa: SLF001
        SharedState(
            candidate_cv_text=_CV_TEXT,
            job_description_text=_JOB_TEXT,
        )
    )

    assert state["writer_attempts"] == MAX_WRITER_ATTEMPTS
    assert state["best_r_total"] == 0.9
    assert state["best_text"] == "second version"
    assert state["best_variance"] == 0.9


async def test_returns_the_best_effort_version_with_its_breakdown() -> None:
    scorer = _FakeMatchScorer(
        [
            _score(0.9),
            _score(0.7),
            _score(0.9, per_dimension={"technical_skills": 0.9}),
            _score(0.6),
        ]
    )
    stub = StubLLMAgentAdapter(
        variance_score=0.9,
        writer_outputs=["first version", "second version", "third version"],
    )
    orchestrator = LangGraphOrchestratorAdapter(stub, match_scorer=scorer)

    optimized = await orchestrator.optimize(_candidate(), _job_description())

    assert optimized.content == "second version"
    assert optimized.variance_score == 0.9
    assert optimized.writer_attempts == MAX_WRITER_ATTEMPTS
    assert optimized.r_total == 0.9
    assert optimized.per_dimension == {"technical_skills": 0.9}
    assert optimized.gap_report == _GAP_TEXT
