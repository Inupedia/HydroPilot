import json

import httpx
import pytest

from hydropilot_api.llm import (
    ChatMessage,
    FunctionToolDefinition,
    LLMProviderError,
    ProviderId,
    ToolChatRequest,
    tool_chat_round,
)


def object_tool() -> FunctionToolDefinition:
    return FunctionToolDefinition(
        name="get_object",
        description="Get one water-network object.",
        parameters={
            "type": "object",
            "properties": {"object_id": {"type": "string"}},
            "required": ["object_id"],
        },
    )


def tool_request(provider: ProviderId = ProviderId.CUSTOM_OPENAI) -> ToolChatRequest:
    return ToolChatRequest(
        provider=provider,
        base_url="https://example.test/v1" if provider is ProviderId.CUSTOM_OPENAI else None,
        api_key="secret" if provider is not ProviderId.OLLAMA else None,
        model="demo-model",
        messages=[ChatMessage(role="user", content="Inspect reservoir-shasta")],
        tools=[object_tool()],
        temperature=0.2,
        max_tokens=700,
    )


def test_openai_compatible_tool_round_sends_native_tool_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://example.test/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer secret"
        body = json.loads(request.content)
        assert body["model"] == "demo-model"
        assert body["messages"] == [{"role": "user", "content": "Inspect reservoir-shasta"}]
        assert body["stream"] is False
        assert body["temperature"] == 0.2
        assert body["max_tokens"] == 700
        assert body["tool_choice"] == "auto"
        assert body["tools"] == [
            {
                "type": "function",
                "function": {
                    "name": "get_object",
                    "description": "Get one water-network object.",
                    "parameters": {
                        "type": "object",
                        "properties": {"object_id": {"type": "string"}},
                        "required": ["object_id"],
                    },
                },
            }
        ]
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
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": "get_object",
                                        "arguments": '{"object_id":"reservoir-shasta"}',
                                    },
                                }
                            ],
                        }
                    }
                ],
                "usage": {"total_tokens": 21},
            },
        )

    response = tool_chat_round(tool_request(), transport=httpx.MockTransport(handler))

    assert response.text is None
    assert response.usage == {"total_tokens": 21}
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].id == "call_1"
    assert response.tool_calls[0].name == "get_object"
    assert response.tool_calls[0].arguments == {"object_id": "reservoir-shasta"}


def test_tool_round_supports_text_only_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "No tool needed."}}],
                "usage": {"total_tokens": 9},
            },
        )

    response = tool_chat_round(tool_request(), transport=httpx.MockTransport(handler))

    assert response.text == "No tool needed."
    assert response.tool_calls == []


def test_tool_round_supports_mixed_text_and_tool_calls():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "I will inspect it.",
                            "tool_calls": [
                                {
                                    "id": "call_2",
                                    "type": "function",
                                    "function": {
                                        "name": "get_object",
                                        "arguments": '{"object_id":"reservoir-shasta"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
        )

    response = tool_chat_round(tool_request(), transport=httpx.MockTransport(handler))

    assert response.text == "I will inspect it."
    assert [item.name for item in response.tool_calls] == ["get_object"]


@pytest.mark.parametrize(
    "arguments",
    [
        "{bad-json",
        '["reservoir-shasta"]',
        '"reservoir-shasta"',
        "null",
    ],
)
def test_tool_round_rejects_malformed_or_non_object_arguments(arguments):
    def handler(request: httpx.Request) -> httpx.Response:
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
                                    "id": "call_bad",
                                    "type": "function",
                                    "function": {"name": "get_object", "arguments": arguments},
                                }
                            ],
                        }
                    }
                ]
            },
        )

    with pytest.raises(LLMProviderError, match="tool call arguments"):
        tool_chat_round(tool_request(), transport=httpx.MockTransport(handler))


@pytest.mark.parametrize(
    "tool_call",
    [
        {
            "id": "",
            "type": "function",
            "function": {"name": "get_object", "arguments": "{}"},
        },
        {
            "id": "call_wrong_type",
            "type": "custom",
            "function": {"name": "get_object", "arguments": "{}"},
        },
        {
            "id": "call_no_name",
            "type": "function",
            "function": {"name": "", "arguments": "{}"},
        },
    ],
)
def test_tool_round_rejects_invalid_tool_call_shape(tool_call):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [tool_call],
                        }
                    }
                ]
            },
        )

    with pytest.raises(LLMProviderError, match="tool call"):
        tool_chat_round(tool_request(), transport=httpx.MockTransport(handler))


def test_tool_round_rejects_empty_assistant_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": []}}]},
        )

    with pytest.raises(LLMProviderError, match="no text or tool calls"):
        tool_chat_round(tool_request(), transport=httpx.MockTransport(handler))


@pytest.mark.parametrize(
    "provider",
    [ProviderId.ANTHROPIC, ProviderId.GEMINI, ProviderId.OLLAMA],
)
def test_tool_round_rejects_unsupported_adapter_before_network(provider):
    network_called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal network_called
        network_called = True
        return httpx.Response(500)

    with pytest.raises(
        LLMProviderError,
        match="tool calling is currently supported only for OpenAI-compatible providers",
    ):
        tool_chat_round(tool_request(provider), transport=httpx.MockTransport(handler))

    assert network_called is False
