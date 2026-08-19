# Native Tool-Call History Design

## Problem

HydroPilot can ask an OpenAI-compatible model for one native tool-call round, and it has a separate read-only Hydro tool registry. A real Agent cannot yet perform a second model round after executing a tool because `ToolChatRequest.messages` only supports ordinary `role + content` chat messages.

OpenAI-compatible tool continuation requires preserving two protocol-native message shapes:

1. the assistant message that proposed `tool_calls`;
2. one `role="tool"` result message per call, keyed by `tool_call_id`.

Flattening tool results into a normal user message would lose call identity and native provider semantics.

## Goal

Allow `tool_chat_round()` to send native assistant-tool-call history and tool-result history while keeping ordinary chat and the existing first-round behavior compatible.

## Design

### Internal message models

Add two typed message models alongside the existing `ChatMessage`:

`ToolAssistantMessage`

- role fixed to `assistant`;
- optional assistant text;
- one or more existing parsed `ToolCall` objects.

`ToolResultMessage`

- role fixed to `tool`;
- non-empty `tool_call_id`;
- string `content`, normally JSON serialized by a future Agent orchestrator.

`ToolChatRequest.messages` accepts ordinary `ChatMessage` plus these two native history models. Ordinary first-round callers remain valid.

### OpenAI wire conversion

The OpenAI-compatible payload adapter converts internal assistant calls from:

`ToolCall(id, name, arguments: dict)`

into the provider-native shape:

- `id`;
- `type = "function"`;
- nested `function.name`;
- nested `function.arguments` serialized as a JSON string.

Tool result messages are emitted as:

- `role = "tool"`;
- `tool_call_id`;
- `content`.

Ordinary `ChatMessage` payloads stay unchanged.

### Scope boundary

This PR only enables protocol history. It does not execute Hydro tools, create an Agent loop, expose a new endpoint, retry calls, or allow write tools.

## Non-goals

- tool execution;
- Agent orchestration;
- scenario/release tools;
- Anthropic/Gemini/Ollama native tool history;
- streaming;
- parallel tool orchestration policy.

## Success criteria

- existing first-round tool-call tests remain unchanged and pass;
- a second-round request can include assistant tool-call history and one or more tool results;
- wire payload uses native OpenAI-compatible tool message shapes;
- tool arguments are encoded as JSON strings on the wire and remain dicts internally;
- repository CI remains green.
