import json

import httpx

from hydropilot_api.llm import (
    ChatMessage,
    FunctionToolDefinition,
    ProviderId,
    ToolAssistantMessage,
    ToolCall,
    ToolChatRequest,
    ToolResultMessage,
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


def test_tool_round_sends_native_assistant_and_tool_result_history():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["messages"] == [
            {"role": "user", "content": "Inspect reservoir-shasta"},
            {
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
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "content": '{"id":"reservoir-shasta","name":"Shasta Lake"}',
            },
        ]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Shasta Lake is the selected reservoir.",
                        }
                    }
                ],
                "usage": {"total_tokens": 42},
            },
        )

    request = ToolChatRequest(
        provider=ProviderId.CUSTOM_OPENAI,
        base_url="https://example.test/v1",
        api_key="secret",
        model="demo-model",
        messages=[
            ChatMessage(role="user", content="Inspect reservoir-shasta"),
            ToolAssistantMessage(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        name="get_object",
                        arguments={"object_id": "reservoir-shasta"},
                    )
                ],
            ),
            ToolResultMessage(
                tool_call_id="call_1",
                content='{"id":"reservoir-shasta","name":"Shasta Lake"}',
            ),
        ],
        tools=[object_tool()],
    )

    response = tool_chat_round(request, transport=httpx.MockTransport(handler))

    assert response.text == "Shasta Lake is the selected reservoir."
    assert response.tool_calls == []
    assert response.usage == {"total_tokens": 42}


def test_tool_history_keeps_arguments_as_dicts_internally():
    call = ToolCall(
        id="call_2",
        name="get_object",
        arguments={"object_id": "reservoir-shasta", "nested": {"enabled": True}},
    )
    message = ToolAssistantMessage(content="Checking.", tool_calls=[call])

    assert message.tool_calls[0].arguments == {
        "object_id": "reservoir-shasta",
        "nested": {"enabled": True},
    }
