import json

import httpx
import pytest
from pydantic import ValidationError

from hydropilot_api.agent import ReadOnlyAgentRequest, run_read_only_agent
from hydropilot_api.domain import Geometry, HydroObject, ObjectType
from hydropilot_api.llm import ChatMessage, ProviderId


class AgentStrictRepository:
    def __init__(self):
        self.object = HydroObject(
            id="reach-a",
            name="Reach A",
            object_type=ObjectType.RIVER_REACH,
            geometry=Geometry(type="LineString", coordinates=[[0.0, 0.0], [1.0, 1.0]]),
        )

    def list_objects(self, object_type=None):
        return [self.object]

    def get_object(self, object_id):
        return self.object if object_id == self.object.id else None

    def list_relations(self):
        return []

    def list_curves(self, object_id=None, curve_type=None):
        return []

    def list_constraints(self, object_id=None, variable=None):
        return []


def request() -> ReadOnlyAgentRequest:
    return ReadOnlyAgentRequest(
        provider=ProviderId.CUSTOM_OPENAI,
        base_url="https://example.test/v1",
        api_key="secret",
        model="demo-model",
        messages=[ChatMessage(role="user", content="Trace reach-a")],
    )


def tool_call(arguments: dict) -> httpx.Response:
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
                                "id": "call_trace",
                                "type": "function",
                                "function": {
                                    "name": "trace_downstream",
                                    "arguments": json.dumps(arguments),
                                },
                            }
                        ],
                    }
                }
            ]
        },
    )


def final_text() -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"role": "assistant", "content": "No downstream objects."}}]},
    )


def test_agent_audit_uses_normalized_args_while_native_history_preserves_model_proposal():
    provider_requests = []

    def handler(http_request: httpx.Request) -> httpx.Response:
        body = json.loads(http_request.content)
        provider_requests.append(body)
        if len(provider_requests) == 1:
            return tool_call({"object_id": "reach-a"})

        assistant_history = next(
            item for item in provider_requests[1]["messages"] if item.get("tool_calls")
        )
        raw_arguments = assistant_history["tool_calls"][0]["function"]["arguments"]
        assert json.loads(raw_arguments) == {"object_id": "reach-a"}
        return final_text()

    result = run_read_only_agent(
        AgentStrictRepository(),
        request(),
        transport=httpx.MockTransport(handler),
    )

    assert result.tool_executions[0].arguments == {
        "object_id": "reach-a",
        "max_hops": 8,
        "offset": 0,
        "limit": 100,
    }


def test_agent_rejects_extra_model_tool_argument_before_follow_up_round():
    provider_calls = 0

    def handler(http_request: httpx.Request) -> httpx.Response:
        nonlocal provider_calls
        provider_calls += 1
        return tool_call({"object_id": "reach-a", "trusted": True})

    with pytest.raises(ValidationError) as exc_info:
        run_read_only_agent(
            AgentStrictRepository(),
            request(),
            transport=httpx.MockTransport(handler),
        )

    assert any(error["type"] == "extra_forbidden" for error in exc_info.value.errors())
    assert provider_calls == 1
