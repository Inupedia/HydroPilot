import json

import httpx
import pytest
from pydantic import ValidationError

from hydropilot_api.agent import ReadOnlyAgentRequest, run_read_only_agent
from hydropilot_api.domain import Geometry, HydroObject, ObjectType
from hydropilot_api.llm import ChatMessage, ProviderId


class LargeResultRepository:
    def __init__(self, blob_size: int):
        self.object = HydroObject(
            id="reservoir-alpha",
            name="Reservoir Alpha",
            object_type=ObjectType.RESERVOIR,
            geometry=Geometry(type="Point", coordinates=[-122.0, 40.0]),
            properties={"blob": "x" * blob_size},
            source="test-repository",
        )

    def list_objects(self, object_type=None):
        if object_type is not None and object_type is not ObjectType.RESERVOIR:
            return []
        return [self.object]

    def get_object(self, object_id):
        return self.object if object_id == self.object.id else None

    def list_relations(self):
        return []

    def list_curves(self, object_id=None, curve_type=None):
        return []

    def list_constraints(self, object_id=None, variable=None):
        return []


def request(*, max_tool_rounds: int = 4) -> ReadOnlyAgentRequest:
    return ReadOnlyAgentRequest(
        provider=ProviderId.CUSTOM_OPENAI,
        base_url="https://example.test/v1",
        api_key="secret",
        model="demo-model",
        messages=[ChatMessage(role="user", content="Inspect reservoir-alpha")],
        max_tool_rounds=max_tool_rounds,
    )


def tool_round(call_ids: list[str]) -> httpx.Response:
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
                                    "name": "get_object",
                                    "arguments": json.dumps({"object_id": "reservoir-alpha"}),
                                },
                            }
                            for call_id in call_ids
                        ],
                    }
                }
            ]
        },
    )


def test_agent_rejects_single_oversized_tool_result_before_follow_up_provider_round():
    network_calls = 0

    def handler(http_request: httpx.Request) -> httpx.Response:
        nonlocal network_calls
        network_calls += 1
        return tool_round(["call_big"])

    with pytest.raises(
        ValueError,
        match="tool result exceeds 24000 character limit for get_object",
    ):
        run_read_only_agent(
            LargeResultRepository(blob_size=24_000),
            request(),
            transport=httpx.MockTransport(handler),
        )

    assert network_calls == 1


def test_agent_rejects_tool_round_aggregate_over_budget_before_follow_up():
    network_calls = 0

    def handler(http_request: httpx.Request) -> httpx.Response:
        nonlocal network_calls
        network_calls += 1
        return tool_round(["call_1", "call_2", "call_3", "call_4"])

    with pytest.raises(
        ValueError,
        match="tool results exceed 48000 character limit for one agent round",
    ):
        run_read_only_agent(
            LargeResultRepository(blob_size=13_000),
            request(),
            transport=httpx.MockTransport(handler),
        )

    assert network_calls == 1


def test_agent_rejects_total_tool_result_budget_across_multiple_rounds():
    network_calls = 0

    def handler(http_request: httpx.Request) -> httpx.Response:
        nonlocal network_calls
        network_calls += 1
        return tool_round([f"call_{network_calls}_a", f"call_{network_calls}_b"])

    with pytest.raises(
        ValueError,
        match="tool results exceed 96000 character limit for one agent run",
    ):
        run_read_only_agent(
            LargeResultRepository(blob_size=13_000),
            request(max_tool_rounds=4),
            transport=httpx.MockTransport(handler),
        )

    assert network_calls == 4


def test_agent_request_does_not_allow_tool_result_budget_override():
    with pytest.raises(ValidationError) as exc_info:
        ReadOnlyAgentRequest.model_validate(
            {
                "provider": "custom-openai",
                "base_url": "https://example.test/v1",
                "api_key": "secret",
                "model": "demo-model",
                "messages": [{"role": "user", "content": "hello"}],
                "max_tool_result_chars": 1_000_000,
            }
        )

    assert any(error["type"] == "extra_forbidden" for error in exc_info.value.errors())
