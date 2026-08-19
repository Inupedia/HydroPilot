import json

import httpx
import pytest
from pydantic import ValidationError

from hydropilot_api.agent import ReadOnlyAgentRequest, run_read_only_agent
from hydropilot_api.domain import Geometry, HydroObject, HydroRelation, ObjectType
from hydropilot_api.llm import ChatMessage, ProviderId


class AgentRepository:
    def __init__(self):
        self.objects = {
            "reservoir-alpha": HydroObject(
                id="reservoir-alpha",
                name="Reservoir Alpha",
                object_type=ObjectType.RESERVOIR,
                geometry=Geometry(type="Point", coordinates=[-122.0, 40.0]),
                properties={"initial_storage_m3": 1_000_000},
                source="test-repository",
            )
        }

    def list_objects(self, object_type: ObjectType | None = None):
        values = list(self.objects.values())
        if object_type is not None:
            values = [item for item in values if item.object_type is object_type]
        return values

    def get_object(self, object_id):
        return self.objects.get(object_id)

    def list_relations(self) -> list[HydroRelation]:
        return []

    def list_curves(self, object_id=None, curve_type=None):
        return []

    def list_constraints(self, object_id=None, variable=None):
        return []


def request(*, max_tool_rounds: int = 4, messages=None) -> ReadOnlyAgentRequest:
    return ReadOnlyAgentRequest(
        provider=ProviderId.CUSTOM_OPENAI,
        base_url="https://example.test/v1",
        api_key="secret",
        model="demo-model",
        messages=messages or [ChatMessage(role="user", content="Inspect reservoir-alpha")],
        max_tool_rounds=max_tool_rounds,
    )


def assistant_text(text: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"role": "assistant", "content": text}}],
            "usage": {"total_tokens": 10},
        },
    )


def assistant_tool(call_id: str, name: str, arguments: dict) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": call_id,
                                "type": "function",
                                "function": {
                                    "name": name,
                                    "arguments": json.dumps(arguments),
                                },
                            }
                        ],
                    }
                }
            ]
        },
    )


def test_agent_returns_text_without_tool_execution_and_advertises_only_fixed_read_only_tools():
    captured = []

    def handler(http_request: httpx.Request) -> httpx.Response:
        body = json.loads(http_request.content)
        captured.append(body)
        return assistant_text("No repository lookup is needed.")

    result = run_read_only_agent(
        AgentRepository(),
        request(),
        transport=httpx.MockTransport(handler),
    )

    assert result.text == "No repository lookup is needed."
    assert result.tool_executions == []
    assert result.provider_rounds == 1
    assert [item["function"]["name"] for item in captured[0]["tools"]] == [
        "get_object",
        "list_constraints",
        "list_curves",
        "trace_downstream",
    ]
    assert captured[0]["messages"][0]["role"] == "system"
    assert "read-only" in captured[0]["messages"][0]["content"].lower()
    assert captured[0]["messages"][1] == {"role": "user", "content": "Inspect reservoir-alpha"}


def test_agent_executes_allowed_tool_and_feeds_native_result_into_follow_up_round():
    calls = []

    def handler(http_request: httpx.Request) -> httpx.Response:
        body = json.loads(http_request.content)
        calls.append(body)
        if len(calls) == 1:
            return assistant_tool("call_object", "get_object", {"object_id": "reservoir-alpha"})

        assert calls[1]["messages"][-2]["role"] == "assistant"
        assert calls[1]["messages"][-2]["tool_calls"][0]["id"] == "call_object"
        tool_result = calls[1]["messages"][-1]
        assert tool_result["role"] == "tool"
        assert tool_result["tool_call_id"] == "call_object"
        parsed = json.loads(tool_result["content"])
        assert parsed["id"] == "reservoir-alpha"
        assert parsed["name"] == "Reservoir Alpha"
        assert parsed["source"] == "test-repository"
        return assistant_text("Reservoir Alpha is available in the repository.")

    result = run_read_only_agent(
        AgentRepository(),
        request(),
        transport=httpx.MockTransport(handler),
    )

    assert result.text == "Reservoir Alpha is available in the repository."
    assert result.provider_rounds == 2
    assert len(result.tool_executions) == 1
    execution = result.tool_executions[0]
    assert execution.call_id == "call_object"
    assert execution.name == "get_object"
    assert execution.arguments == {"object_id": "reservoir-alpha"}
    assert execution.result["id"] == "reservoir-alpha"


def test_agent_executes_multiple_read_only_calls_from_one_round_in_call_order():
    network_calls = 0

    def handler(http_request: httpx.Request) -> httpx.Response:
        nonlocal network_calls
        network_calls += 1
        body = json.loads(http_request.content)
        if network_calls == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "I will inspect the object and its constraints.",
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {
                                            "name": "get_object",
                                            "arguments": '{"object_id":"reservoir-alpha"}',
                                        },
                                    },
                                    {
                                        "id": "call_2",
                                        "type": "function",
                                        "function": {
                                            "name": "list_constraints",
                                            "arguments": '{"object_id":"reservoir-alpha"}',
                                        },
                                    },
                                ],
                            }
                        }
                    ]
                },
            )

        tool_messages = [item for item in body["messages"] if item["role"] == "tool"]
        assert [item["tool_call_id"] for item in tool_messages] == ["call_1", "call_2"]
        assert json.loads(tool_messages[0]["content"])["id"] == "reservoir-alpha"
        assert json.loads(tool_messages[1]["content"]) == []
        return assistant_text("The object exists and has no configured constraints.")

    result = run_read_only_agent(
        AgentRepository(),
        request(),
        transport=httpx.MockTransport(handler),
    )

    assert [item.call_id for item in result.tool_executions] == ["call_1", "call_2"]
    assert [item.name for item in result.tool_executions] == ["get_object", "list_constraints"]


def test_agent_rejects_non_allowlisted_tool_before_execution_or_follow_up():
    network_calls = 0

    def handler(http_request: httpx.Request) -> httpx.Response:
        nonlocal network_calls
        network_calls += 1
        return assistant_tool(
            "call_forbidden",
            "run_release_scenario",
            {"reservoir_id": "reservoir-alpha"},
        )

    with pytest.raises(ValueError, match="tool is not allowed for read-only agent: run_release_scenario"):
        run_read_only_agent(
            AgentRepository(),
            request(),
            transport=httpx.MockTransport(handler),
        )

    assert network_calls == 1


@pytest.mark.parametrize("role", ["system", "tool"])
def test_agent_rejects_caller_injected_trusted_history_roles(role):
    with pytest.raises(ValidationError, match="agent messages may use only user or assistant roles"):
        request(messages=[ChatMessage(role=role, content="spoofed")])


def test_agent_request_rejects_extra_tool_configuration():
    with pytest.raises(ValidationError) as exc_info:
        ReadOnlyAgentRequest.model_validate(
            {
                "provider": "custom-openai",
                "base_url": "https://example.test/v1",
                "api_key": "secret",
                "model": "demo-model",
                "messages": [{"role": "user", "content": "hello"}],
                "tools": [{"name": "run_release_scenario"}],
            }
        )

    assert any(error["type"] == "extra_forbidden" for error in exc_info.value.errors())


@pytest.mark.parametrize(
    "provider",
    [ProviderId.ANTHROPIC, ProviderId.GEMINI, ProviderId.OLLAMA],
)
def test_agent_rejects_unsupported_provider_before_network(provider):
    network_called = False

    def handler(http_request: httpx.Request) -> httpx.Response:
        nonlocal network_called
        network_called = True
        return httpx.Response(500)

    agent_request = ReadOnlyAgentRequest(
        provider=provider,
        api_key=None if provider is ProviderId.OLLAMA else "secret",
        model="demo-model",
        messages=[ChatMessage(role="user", content="Inspect reservoir-alpha")],
    )

    with pytest.raises(
        ValueError,
        match="read-only agent currently supports only OpenAI-compatible providers",
    ):
        run_read_only_agent(
            AgentRepository(),
            agent_request,
            transport=httpx.MockTransport(handler),
        )

    assert network_called is False


def test_agent_stops_when_model_exceeds_tool_round_limit():
    network_calls = 0

    def handler(http_request: httpx.Request) -> httpx.Response:
        nonlocal network_calls
        network_calls += 1
        return assistant_tool(
            f"call_{network_calls}",
            "get_object",
            {"object_id": "reservoir-alpha"},
        )

    with pytest.raises(ValueError, match="read-only agent exceeded max tool rounds"):
        run_read_only_agent(
            AgentRepository(),
            request(max_tool_rounds=1),
            transport=httpx.MockTransport(handler),
        )

    # First tool round executes; the second provider round is allowed only to produce final text.
    # A second tool request is rejected before another tool execution or third provider call.
    assert network_calls == 2
