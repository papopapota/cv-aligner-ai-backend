import asyncio
from collections.abc import Mapping

import pytest

from src.application.ports.out.llm_agent_port import AgentRole
from src.application.ports.out.match_scorer_port import MatchScorerPort
from src.domain.audit_rules import MAX_VARIANCE_THRESHOLD, MAX_WRITER_ATTEMPTS
from src.domain.candidate_cv import CandidateCV
from src.domain.compatibility_score import CompatibilityScore
from src.domain.errors import InvalidUploadError
from src.domain.job_description import JobDescription
from src.domain.semantic_profile import SemanticProfile
from src.domain.shared_state import SharedState
from src.domain.uploaded_file_metadata import UploadedFileMetadata
from src.infrastructure.adapters.out.langgraph_orchestrator_adapter import (
    LangGraphOrchestratorAdapter,
    parse_audit_reason,
    parse_semantic_profile,
    parse_variance_score,
)
from src.infrastructure.adapters.out.stub_llm_agent_adapter import (
    StubLLMAgentAdapter,
)

_CV_TEXT = "Python backend engineer with fastapi."
_JOB_TEXT = "Looking for a FastAPI developer."
_GAP_TEXT = "GAP ANALYSIS: missing kubernetes and postgres depth."
_WRITER_TEXT = "OPTIMIZED CV: python backend engineer with fastapi and postgres."


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
    original_variance_score: float = 0.8,
    variance_threshold: float = MAX_VARIANCE_THRESHOLD,
) -> LangGraphOrchestratorAdapter:
    return LangGraphOrchestratorAdapter(
        StubLLMAgentAdapter(
            variance_score=variance_score,
            variance_score_on_first_attempt=variance_score_on_first_attempt,
            original_variance_score=original_variance_score,
        ),
        variance_threshold=variance_threshold,
    )


def _score(
    ic: float,
    per_dimension: dict[str, float] | None = None,
) -> CompatibilityScore:
    return CompatibilityScore(
        ncos=min(ic / 100.0, 1.0),
        ntfidf=0.0,
        neuc=0.0,
        ic=ic,
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

    assert optimized.original_variance_score == 0.8
    assert optimized.optimized_variance_score == 0.1
    assert optimized.writer_attempts == 1
    assert optimized.is_within_threshold()
    assert optimized.content
    assert optimized.original_ic is None
    assert optimized.optimized_ic is None
    assert optimized.original_per_dimension == {}
    assert optimized.optimized_per_dimension == {}
    assert optimized.gap_report == _GAP_TEXT


async def test_retries_the_writer_once_when_the_variance_is_high() -> None:
    optimized = await _orchestrator(
        variance_score=0.1,
        variance_score_on_first_attempt=0.9,
    ).optimize(_candidate(), _job_description())

    assert optimized.writer_attempts == 2
    assert optimized.optimized_variance_score == 0.1


async def test_stops_retrying_at_the_attempt_cap() -> None:
    optimized = await _orchestrator(variance_score=0.9).optimize(
        _candidate(),
        _job_description(),
    )

    assert optimized.writer_attempts == MAX_WRITER_ATTEMPTS
    assert optimized.original_variance_score == 0.8
    assert optimized.optimized_variance_score == 0.9
    assert not optimized.is_within_threshold()


async def test_approves_with_a_more_permissive_threshold() -> None:
    optimized = await _orchestrator(
        variance_score=0.9,
        variance_threshold=0.95,
    ).optimize(_candidate(), _job_description())

    assert optimized.writer_attempts == 1
    assert optimized.is_within_threshold()


async def test_the_writer_retry_receives_the_previous_cv_and_audit_reason() -> None:
    calls: list[tuple[AgentRole, str]] = []

    class _Recorder(StubLLMAgentAdapter):
        async def complete(self, role: AgentRole, prompt: str) -> str:
            calls.append((role, prompt))
            return await super().complete(role, prompt)

    orchestrator = LangGraphOrchestratorAdapter(
        _Recorder(variance_score=0.1, variance_score_on_first_attempt=0.9)
    )

    await orchestrator.optimize(_candidate(), _job_description())

    writer_prompts = [prompt for role, prompt in calls if role is AgentRole.WRITER]
    assert len(writer_prompts) == 2
    assert _WRITER_TEXT in writer_prompts[1]
    assert "VARIANCE SCORE: 0.9" in writer_prompts[1]


async def test_runs_the_nodes_with_the_expected_dependencies() -> None:
    calls: list[tuple[AgentRole, str]] = []

    class _Recorder(StubLLMAgentAdapter):
        async def complete(self, role: AgentRole, prompt: str) -> str:
            calls.append((role, prompt))
            return await super().complete(role, prompt)

    orchestrator = LangGraphOrchestratorAdapter(_Recorder(variance_score=0.1))

    await orchestrator.optimize(_candidate(), _job_description())

    extractor = next(
        (role, prompt)
        for role, prompt in calls
        if role is AgentRole.EXTRACTOR
    )
    analyzer = next(
        (role, prompt) for role, prompt in calls if role is AgentRole.ANALYZER
    )
    original_auditor = next(
        (role, prompt)
        for role, prompt in calls
        if role is AgentRole.AUDITOR and "Original CV:" in prompt
    )
    writer = next(
        (role, prompt) for role, prompt in calls if role is AgentRole.WRITER
    )
    optimized_auditor = next(
        (role, prompt)
        for role, prompt in calls
        if role is AgentRole.AUDITOR and "Optimized CV:" in prompt
    )

    assert calls.index(extractor) < calls.index(analyzer)
    assert calls.index(extractor) < calls.index(writer)
    assert calls.index(analyzer) < calls.index(writer)
    assert calls.index(original_auditor) < calls.index(writer)
    assert calls.index(writer) < calls.index(optimized_auditor)

    assert _CV_TEXT in extractor[1]
    assert _JOB_TEXT in analyzer[1]
    assert _JOB_TEXT in original_auditor[1]
    assert _CV_TEXT in original_auditor[1]
    assert _JOB_TEXT in writer[1]
    assert _GAP_TEXT in writer[1]
    assert _JOB_TEXT in optimized_auditor[1]
    assert _GAP_TEXT in optimized_auditor[1]


async def test_the_original_audit_runs_concurrently_with_extraction() -> None:
    barrier = asyncio.Barrier(2)

    class _Concurrent(StubLLMAgentAdapter):
        async def complete(self, role: AgentRole, prompt: str) -> str:
            is_original_audit = role is AgentRole.AUDITOR and "Original CV:" in prompt
            if role is AgentRole.EXTRACTOR or is_original_audit:
                await asyncio.wait_for(barrier.wait(), timeout=2)
            return await super().complete(role, prompt)

    orchestrator = LangGraphOrchestratorAdapter(_Concurrent(variance_score=0.1))

    optimized = await orchestrator.optimize(_candidate(), _job_description())

    assert optimized.original_variance_score == 0.8
    assert optimized.writer_attempts == 1


async def test_the_original_cv_is_audited_once_before_writing() -> None:
    calls: list[tuple[AgentRole, str]] = []

    class _Recorder(StubLLMAgentAdapter):
        async def complete(self, role: AgentRole, prompt: str) -> str:
            calls.append((role, prompt))
            return await super().complete(role, prompt)

    orchestrator = LangGraphOrchestratorAdapter(
        _Recorder(
            variance_score=0.1,
            variance_score_on_first_attempt=0.9,
            original_variance_score=0.7,
        )
    )

    optimized = await orchestrator.optimize(_candidate(), _job_description())

    original_audits = [
        prompt
        for role, prompt in calls
        if role is AgentRole.AUDITOR and "Original CV:" in prompt
    ]
    optimized_audits = [
        prompt
        for role, prompt in calls
        if role is AgentRole.AUDITOR and "Optimized CV:" in prompt
    ]
    assert len(original_audits) == 1
    assert len(optimized_audits) == 2
    assert optimized.original_variance_score == 0.7


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


def test_parses_the_reason_from_a_json_audit() -> None:
    audit = '{"variance_score": 0.4, "reason": "missing kubernetes"}'

    assert parse_audit_reason(audit) == "missing kubernetes"


def test_falls_back_to_the_raw_audit_as_reason() -> None:
    assert parse_audit_reason("Variance below 0.20") == "Variance below 0.20"


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


async def test_approves_when_variance_and_ic_meet_the_targets() -> None:
    scorer = _FakeMatchScorer([_score(90.0), _score(90.0)])
    orchestrator = LangGraphOrchestratorAdapter(
        StubLLMAgentAdapter(variance_score=0.1),
        match_scorer=scorer,
    )

    optimized = await orchestrator.optimize(_candidate(), _job_description())

    assert optimized.writer_attempts == 1
    assert optimized.optimized_variance_score == 0.1
    assert optimized.is_within_threshold()
    assert len(scorer.calls) == 2
    assert scorer.calls[0][0] == _CV_TEXT
    assert scorer.calls[1][0] == optimized.content
    assert scorer.calls[0][2] == {
        "technical_skills": "python, fastapi",
        "experience": "backend engineering",
    }


async def test_retries_when_the_ic_is_below_the_target() -> None:
    scorer = _FakeMatchScorer([_score(90.0), _score(50.0), _score(50.0), _score(50.0)])
    orchestrator = LangGraphOrchestratorAdapter(
        StubLLMAgentAdapter(variance_score=0.1),
        match_scorer=scorer,
    )

    optimized = await orchestrator.optimize(_candidate(), _job_description())

    assert optimized.writer_attempts == MAX_WRITER_ATTEMPTS
    assert len(scorer.calls) == 1 + MAX_WRITER_ATTEMPTS


async def test_respects_a_custom_ic_target() -> None:
    scorer = _FakeMatchScorer([_score(90.0), _score(84.0)])
    orchestrator = LangGraphOrchestratorAdapter(
        StubLLMAgentAdapter(variance_score=0.1),
        match_scorer=scorer,
        ic_target=80.0,
    )

    optimized = await orchestrator.optimize(_candidate(), _job_description())

    assert optimized.writer_attempts == 1


async def test_retries_when_the_variance_is_high_with_scoring_enabled() -> None:
    scorer = _FakeMatchScorer(
        [_score(90.0), _score(90.0), _score(90.0), _score(90.0)]
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
        [_score(90.0, per_dimension={"technical_skills": 0.42}), _score(90.0)]
    )
    orchestrator = LangGraphOrchestratorAdapter(
        _Recorder(variance_score=0.1),
        match_scorer=scorer,
    )

    await orchestrator.optimize(_candidate(), _job_description())

    analysis_prompts = [
        prompt for prompt in prompts if "Baseline match (IC=" in prompt
    ]
    assert len(analysis_prompts) == 1
    analysis_prompt = analysis_prompts[0]
    assert "technical_skills: 0.420" in analysis_prompt
    assert "Prioriza cerrar las brechas" in analysis_prompt


async def test_extracts_the_job_profile_with_an_extra_explorer_call() -> None:
    prompts: list[str] = []

    class _Recorder(StubLLMAgentAdapter):
        async def complete(self, role: AgentRole, prompt: str) -> str:
            prompts.append(prompt)
            return await super().complete(role, prompt)

    scorer = _FakeMatchScorer([_score(90.0), _score(90.0)])
    orchestrator = LangGraphOrchestratorAdapter(
        _Recorder(variance_score=0.1),
        match_scorer=scorer,
    )

    await orchestrator.optimize(_candidate(), _job_description())

    assert len(prompts) == 7
    assert any(prompt == f"Job description:\n{_JOB_TEXT}" for prompt in prompts)
    assert any(prompt.startswith("Optimized CV:\n") for prompt in prompts)
    assert scorer.calls[0][3] == {
        "technical_skills": "python, fastapi",
        "experience": "backend engineering",
    }


async def test_tracks_the_best_version_while_retrying() -> None:
    scorer = _FakeMatchScorer([_score(90.0), _score(70.0), _score(90.0), _score(60.0)])
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
    assert state["best_ic"] == 90.0
    assert state["best_text"] == "second version"
    assert state["best_variance"] == 0.9


async def test_returns_the_best_effort_version_with_its_breakdown() -> None:
    scorer = _FakeMatchScorer(
        [
            _score(90.0),
            _score(70.0),
            _score(90.0, per_dimension={"technical_skills": 0.9}),
            _score(60.0),
        ]
    )
    stub = StubLLMAgentAdapter(
        variance_score=0.9,
        writer_outputs=["first version", "second version", "third version"],
    )
    orchestrator = LangGraphOrchestratorAdapter(stub, match_scorer=scorer)

    optimized = await orchestrator.optimize(_candidate(), _job_description())

    assert optimized.content == "second version"
    assert optimized.optimized_variance_score == 0.9
    assert optimized.writer_attempts == MAX_WRITER_ATTEMPTS
    assert optimized.original_ic == 90.0
    assert optimized.optimized_ic == 90.0
    assert optimized.original_per_dimension == {}
    assert optimized.optimized_per_dimension == {"technical_skills": 0.9}
    assert optimized.gap_report == _GAP_TEXT


async def test_returns_the_ic_before_and_after_optimizing() -> None:
    scorer = _FakeMatchScorer(
        [
            _score(61.0, per_dimension={"technical_skills": 0.3}),
            _score(84.0, per_dimension={"technical_skills": 0.9}),
        ]
    )
    orchestrator = LangGraphOrchestratorAdapter(
        StubLLMAgentAdapter(variance_score=0.1),
        match_scorer=scorer,
    )

    optimized = await orchestrator.optimize(_candidate(), _job_description())

    assert optimized.original_ic == 61.0
    assert optimized.optimized_ic == 84.0
    assert optimized.original_per_dimension == {"technical_skills": 0.3}
    assert optimized.optimized_per_dimension == {"technical_skills": 0.9}
