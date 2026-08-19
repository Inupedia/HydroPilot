# OpenAI-Compatible Tool-Calling Round Design

## Problem

HydroPilot now has a typed read-only Hydro tool registry, but its LLM adapter can only exchange plain text. OpenAI-compatible chat-completions providers can natively return function/tool calls, yet the current adapter neither sends tool definitions nor parses tool-call responses.

Jumping directly to an Agent loop would mix provider protocol handling, tool execution, conversation orchestration, and safety semantics in one change.

## Goal

Add one native tool-capable chat round for OpenAI-compatible providers. The round may return text, tool calls, or both, but it does not execute any tool and does not iterate the conversation.

This creates a provider-protocol primitive that a later Agent orchestrator can compose with the Hydro tool registry.

## Request model

Add a generic function-tool definition with:

- `name`;
- `description`;
- `parameters` JSON Schema object.

Add `ToolChatRequest` extending the existing chat request fields with a non-empty `tools` list.

The normal `ChatRequest` and `chat_completion()` behavior remain unchanged.

## OpenAI-compatible wire format

For OpenAI-compatible providers, send the normal chat-completions payload plus:

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_object",
        "description": "...",
        "parameters": {"type": "object", "properties": {}}
      }
    }
  ],
  "tool_choice": "auto"
}
```

Temperature/max-token behavior remains consistent with the existing OpenAI-compatible adapter.

## Response model

`ToolChatResponse` contains:

- provider;
- model;
- optional text;
- zero or more parsed `ToolCall` records;
- optional usage metadata.

Each parsed `ToolCall` contains:

- call id;
- function name;
- arguments as a JSON object/dictionary.

## Tool-call parsing

OpenAI-compatible responses encode `function.arguments` as a JSON string. The adapter parses that string with strict JSON decoding.

Reject as `LLMProviderError` when:

- response structure is missing or malformed;
- a tool call has no non-empty id;
- a tool call is not a `function` tool;
- function name is missing/empty;
- arguments are malformed JSON;
- decoded arguments are not a JSON object.

A response is valid when it contains non-empty text, at least one tool call, or both. A response containing neither is rejected.

## Provider support boundary

This PR supports tool calling only when the configured provider uses `AdapterFamily.OPENAI_COMPATIBLE`, which currently includes OpenAI, DeepSeek, SiliconFlow, OpenRouter, and custom OpenAI-compatible endpoints.

Anthropic, Gemini, and Ollama tool protocols are intentionally not emulated or translated in this PR. Calling `tool_chat_round()` with those adapters fails explicitly before any network request.

## Safety boundary

This primitive only returns proposed tool calls. It never executes them, never accesses `HydroRepository`, never invokes scenario/model execution, and never loops automatically.

A subsequent Agent PR will decide which registered tools may be executed and how tool results are fed back into the model.

## Scope

- LLM protocol models/payload/parser;
- one OpenAI-compatible tool chat round;
- focused mock-transport tests.

## Non-goals

- Hydro tool execution;
- Agent loop/orchestration;
- tool-calling HTTP endpoint;
- Anthropic/Gemini/Ollama tool support;
- streaming;
- write/model-execution tools;
- Studio changes.

## Success criteria

- OpenAI-compatible request emits native `tools` and `tool_choice=auto`;
- valid tool-call JSON arguments are parsed to dictionaries;
- text-only and mixed text/tool responses are supported;
- malformed/non-object tool arguments fail explicitly;
- unsupported adapter families fail before network access;
- existing plain-text chat adapters remain unchanged;
- repository CI remains green.
