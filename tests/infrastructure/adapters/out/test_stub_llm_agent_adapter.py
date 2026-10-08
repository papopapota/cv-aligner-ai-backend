from src.application.ports.out.llm_agent_port import AgentRole
from src.infrastructure.adapters.out.stub_llm_agent_adapter import (
    StubLLMAgentAdapter,
)


async def test_returns_a_response_for_every_role() -> None:
    adapter = StubLLMAgentAdapter()

    for role in AgentRole:
        response = await adapter.complete(role, "prompt")

        assert response


async def test_returns_the_configured_variance_on_the_auditor() -> None:
    adapter = StubLLMAgentAdapter(variance_score=0.42)

    response = await adapter.complete(AgentRole.AUDITOR, "prompt")

    assert "0.42" in response


async def test_uses_the_first_attempt_variance_once_then_falls_back() -> None:
    adapter = StubLLMAgentAdapter(
        variance_score=0.1,
        variance_score_on_first_attempt=0.9,
    )

    first = await adapter.complete(AgentRole.AUDITOR, "prompt")
    second = await adapter.complete(AgentRole.AUDITOR, "prompt")
    third = await adapter.complete(AgentRole.AUDITOR, "prompt")

    assert "0.9" in first
    assert "0.1" in second
    assert "0.1" in third


async def test_is_deterministic_for_the_creative_roles() -> None:
    adapter = StubLLMAgentAdapter()

    first = await adapter.complete(AgentRole.WRITER, "prompt")
    second = await adapter.complete(AgentRole.WRITER, "prompt")

    assert first == second
