import json
from typing import Callable

import httpx2
import pytest
from openai import AsyncOpenAI

from src.application.ports.out.llm_agent_port import AgentRole
from src.infrastructure.adapters.out.openai_llm_agent_adapter import (
    LLMError,
    OpenAILLMAgentAdapter,
)

_model = "gpt-test"
_default_max_tokens = 64

_expected_temperatures: dict[AgentRole, float] = {
    AgentRole.EXTRACTOR: 0.3,
    AgentRole.ANALYZER: 0.3,
    AgentRole.WRITER: 0.7,
    AgentRole.AUDITOR: 0.0,
}

_max_tokens_overrides: dict[AgentRole, int] = {
    AgentRole.EXTRACTOR: 800,
    AgentRole.ANALYZER: 800,
    AgentRole.AUDITOR: 300,
}

_expected_max_tokens: dict[AgentRole, int] = {
    AgentRole.EXTRACTOR: 800,
    AgentRole.ANALYZER: 800,
    AgentRole.WRITER: _default_max_tokens,
    AgentRole.AUDITOR: 300,
}


def _completion_response(content: str | None) -> dict[str, object]:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 0,
        "model": _model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }


def _build_adapter(
    handler: Callable[[httpx2.Request], httpx2.Response],
) -> tuple[OpenAILLMAgentAdapter, list[httpx2.Request]]:
    captured: list[httpx2.Request] = []

    def recording_handler(request: httpx2.Request) -> httpx2.Response:
        captured.append(request)
        return handler(request)

    transport = httpx2.MockTransport(recording_handler)
    client = AsyncOpenAI(
        api_key="test-key",
        base_url="http://null",
        http_client=httpx2.AsyncClient(transport=transport, base_url="http://null"),
    )
    adapter = OpenAILLMAgentAdapter(
        client=client,
        model=_model,
        max_tokens=_default_max_tokens,
        max_tokens_by_role=_max_tokens_overrides,
    )
    return adapter, captured


@pytest.mark.parametrize("role", list(AgentRole))
async def test_sends_system_and_user_messages(role: AgentRole) -> None:
    adapter, captured = _build_adapter(
        lambda request: httpx2.Response(
            200,
            json=_completion_response("answer"),
        )
    )

    await adapter.complete(role, "input text")

    body = json.loads(captured[0].content)
    messages = body["messages"]
    assert messages[0]["role"] == "system"
    assert "input text" in messages[1]["content"]
    assert messages[1]["role"] == "user"


@pytest.mark.parametrize("role", list(AgentRole))
async def test_uses_the_model_and_the_temperature_configured_per_role(
    role: AgentRole,
) -> None:
    adapter, captured = _build_adapter(
        lambda request: httpx2.Response(
            200,
            json=_completion_response("answer"),
        )
    )

    await adapter.complete(role, "input text")

    body = json.loads(captured[0].content)
    assert body["model"] == _model
    assert body["temperature"] == _expected_temperatures[role]


@pytest.mark.parametrize("role", list(AgentRole))
async def test_uses_the_max_tokens_override_or_the_default_per_role(
    role: AgentRole,
) -> None:
    adapter, captured = _build_adapter(
        lambda request: httpx2.Response(
            200,
            json=_completion_response("answer"),
        )
    )

    await adapter.complete(role, "input text")

    body = json.loads(captured[0].content)
    assert body["max_tokens"] == _expected_max_tokens[role]


async def test_returns_the_model_content() -> None:
    adapter, _ = _build_adapter(
        lambda request: httpx2.Response(
            200,
            json=_completion_response("optimized cv body"),
        )
    )

    result = await adapter.complete(AgentRole.WRITER, "optimize")

    assert result == "optimized cv body"


async def test_raises_when_the_model_returns_no_content() -> None:
    adapter, _ = _build_adapter(
        lambda request: httpx2.Response(
            200,
            json=_completion_response(None),
        )
    )

    with pytest.raises(LLMError):
        await adapter.complete(AgentRole.WRITER, "optimize")


async def test_wraps_http_errors_with_the_role_and_model() -> None:
    adapter, _ = _build_adapter(
        lambda request: httpx2.Response(
            500,
            json={"error": {"message": "boom", "type": "server_error"}},
        )
    )

    with pytest.raises(LLMError, match="writer.*gpt-test"):
        await adapter.complete(AgentRole.WRITER, "optimize")