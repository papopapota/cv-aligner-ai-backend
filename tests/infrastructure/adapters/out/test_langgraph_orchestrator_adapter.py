import pytest

from src.domain.audit_rules import MAX_WRITER_ATTEMPTS
from src.domain.candidate_cv import CandidateCV
from src.domain.errors import InvalidUploadError
from src.domain.job_description import JobDescription
from src.domain.uploaded_file_metadata import UploadedFileMetadata
from src.infrastructure.adapters.out.langgraph_orchestrator_adapter import (
    LangGraphOrchestratorAdapter,
)
from src.infrastructure.adapters.out.stub_llm_agent_adapter import (
    StubLLMAgentAdapter,
)

_CV_TEXT = "Python backend engineer with fastapi."
_JOB_TEXT = "Looking for a FastAPI developer."


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


def _orchestrator(**stub_kwargs: object) -> LangGraphOrchestratorAdapter:
    return LangGraphOrchestratorAdapter(StubLLMAgentAdapter(**stub_kwargs))


async def test_runs_the_whole_graph_and_approves_a_low_variance() -> None:
    optimized = await _orchestrator(variance_score=0.1).optimize(
        _candidate(),
        _job_description(),
    )

    assert optimized.variance_score == 0.1
    assert optimized.writer_attempts == 1
    assert optimized.is_within_threshold()
    assert optimized.content


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
    llm_agent = StubLLMAgentAdapter(variance_score=0.1)
    prompts: list[str] = []

    class _Recorder(StubLLMAgentAdapter):
        async def complete(self, role, prompt: str) -> str:
            prompts.append(prompt)
            return await super().complete(role, prompt)

    orchestrator = LangGraphOrchestratorAdapter(_Recorder(variance_score=0.1))

    await orchestrator.optimize(_candidate(), _job_description())

    assert len(prompts) == 4
    assert _CV_TEXT in prompts[0]
    assert _JOB_TEXT in prompts[1]


async def test_rejects_an_audit_without_a_numeric_score() -> None:
    class _NoScore(StubLLMAgentAdapter):
        async def complete(self, role, prompt: str) -> str:
            if role.value == "auditor":
                return "I cannot tell"
            return await super().complete(role, prompt)

    orchestrator = LangGraphOrchestratorAdapter(_NoScore(variance_score=0.1))

    with pytest.raises(InvalidUploadError):
        await orchestrator.optimize(_candidate(), _job_description())
