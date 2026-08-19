# Native Tool-Call History Implementation Plan

## File structure

- `apps/api/tests/test_llm_tool_history.py` — RED/GREEN follow-up protocol-history payload coverage.
- `apps/api/tests/test_llm_tools.py` — existing first-round regression coverage remains authoritative.
- `apps/api/src/hydropilot_api/llm.py` — typed history messages and OpenAI wire conversion.

## Task 1 — RED

Add tests proving:

1. existing first-round `ChatMessage` requests continue to produce the same payload through existing tests;
2. an assistant tool-call history message serializes to native OpenAI `tool_calls` shape;
3. a tool result serializes with `role=tool`, `tool_call_id`, and content;
4. parsed tool arguments remain dicts internally but are JSON strings on the provider wire;
5. a follow-up round can return final text after tool history.

Expected state: the new history test fails because native assistant/tool-result message models and serialization do not exist.

## Task 2 — GREEN

- reuse `ToolCall` in two `ChatMessage` subclasses;
- add `ToolAssistantMessage` and `ToolResultMessage` without changing the existing `ToolChatRequest.messages` field contract;
- rely on the existing base-message compatibility for internally constructed subtype instances;
- add an OpenAI-specific message serializer for tool rounds;
- keep plain `ChatRequest` payload behavior unchanged.

Do not execute tools or add an Agent loop in this PR.

## Task 3 — verification

- inspect the complete diff;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
