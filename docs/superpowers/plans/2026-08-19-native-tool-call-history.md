# Native Tool-Call History Implementation Plan

## File structure

- `apps/api/tests/test_llm_tools.py` — RED/GREEN protocol-history payload coverage.
- `apps/api/src/hydropilot_api/llm.py` — typed history messages and OpenAI wire conversion.

## Task 1 — RED

Add tests proving:

1. an existing first-round `ChatMessage` request still produces the same payload;
2. an assistant tool-call history message serializes to native OpenAI `tool_calls` shape;
3. a tool result serializes with `role=tool`, `tool_call_id`, and content;
4. parsed tool arguments remain dicts internally but are JSON strings on the provider wire;
5. a follow-up round can return final text after tool history.

Expected state: the history test fails because `ToolChatRequest.messages` cannot represent native tool-call/tool-result messages.

## Task 2 — GREEN

- move/reuse `ToolCall` so it can be referenced by message models;
- add `ToolAssistantMessage` and `ToolResultMessage`;
- widen only `ToolChatRequest.messages` to accept ordinary and native tool-history messages;
- add an OpenAI-specific message serializer for tool rounds;
- keep plain `ChatRequest` payload behavior unchanged.

Do not execute tools or add an Agent loop in this PR.

## Task 3 — verification

- inspect the complete diff;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
