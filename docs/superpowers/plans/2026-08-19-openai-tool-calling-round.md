# OpenAI-Compatible Tool-Calling Round Implementation Plan

## File structure

- `apps/api/src/hydropilot_api/llm.py` — generic tool request/response models, OpenAI-compatible payload/parser, and one-round call.
- `apps/api/tests/test_llm_tools.py` — RED/GREEN payload, parsing, error, and provider-boundary tests.
- existing `apps/api/tests/test_llm.py` — unchanged plain-chat regression coverage remains authoritative.

## Task 1 — RED

Add tests proving:

1. OpenAI-compatible tool round sends native `tools` entries and `tool_choice=auto`;
2. model/tool/temperature/max-token/message fields remain correct;
3. a returned function call parses its JSON-string arguments into a dictionary;
4. text-only response returns no tool calls;
5. mixed text + tool calls is supported;
6. malformed JSON arguments fail as `LLMProviderError`;
7. JSON arguments decoding to a non-object fail explicitly;
8. missing/invalid tool call id, type, or function name fail explicitly;
9. Anthropic, Gemini, and Ollama fail as unsupported before network access.

Expected state: tests fail because no tool-capable LLM round exists.

## Task 2 — GREEN models/payload/parser

Implement:

- `FunctionToolDefinition`;
- `ToolChatRequest`;
- `ToolCall`;
- `ToolChatResponse`;
- OpenAI-compatible native tools payload;
- strict tool-call response parsing.

Keep existing `ChatRequest`, `ChatResponse`, `_openai_payload`, and plain-chat extractors behavior compatible.

## Task 3 — GREEN one-round transport

Add `tool_chat_round()`:

- reject non-OpenAI-compatible adapter families before credential/network work;
- reuse existing credential resolution;
- POST to the provider's `/chat/completions` endpoint;
- preserve existing HTTP error semantics;
- return parsed text/tool calls without executing them.

Do not add an API route or Agent loop.

## Task 4 — verification

- inspect diff for tool execution/repository coupling or changes to non-OpenAI provider adapters;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
