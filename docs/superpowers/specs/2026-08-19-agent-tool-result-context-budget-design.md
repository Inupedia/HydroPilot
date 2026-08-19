# Agent Tool-Result Context Budget Design

## Problem

HydroPilot's read-only Agent feeds JSON tool results back to the model using native `role="tool"` messages. Individual tools are increasingly shaped for compact results, but the orchestration layer still trusts every current and future tool result to be small enough for model context.

A large object property, curve collection, or future read-only tool could return tens or hundreds of thousands of characters. Multiple calls in one round can multiply that payload. Blindly forwarding those results can exhaust model context, increase latency/cost, or make the Agent unreliable.

## Goal

Add a fixed orchestration-level character budget for tool results before they enter native LLM history.

The budget is intentionally controlled by server code. Callers cannot raise it through `ReadOnlyAgentRequest`.

## Budgets

Define conservative fixed limits:

- maximum serialized JSON characters for one tool result: **24,000**;
- maximum serialized JSON characters across all tool results in one provider tool round: **48,000**;
- maximum serialized JSON characters across the complete Agent run: **96,000**.

Character count is used instead of estimated tokens because it is deterministic, provider-independent, and easy to test. It is a safety ceiling, not a precise token-budget calculation.

## Serialization

Use the same deterministic JSON representation already used for native tool-result history:

- `ensure_ascii=False`;
- compact separators;
- sorted keys.

Budget checks are performed on that exact serialized string, so the measured payload equals what would be sent to the provider.

## Failure behavior

Do **not** truncate tool JSON.

Truncating could create incomplete data while making the result appear valid. Instead, fail explicitly with `ValueError` before the oversized result is appended to model history or another provider round begins.

Distinct error messages identify:

- per-result limit exceeded, including tool name;
- per-round aggregate limit exceeded;
- total Agent-run tool-result limit exceeded.

The existing `/api/agent/chat` boundary maps deterministic Agent `ValueError` failures to HTTP 422.

## Execution order

For every tool-containing provider round:

1. execute each already-allowlisted read-only tool sequentially;
2. deterministically serialize its result;
3. check per-result limit;
4. check prospective round aggregate limit;
5. check prospective Agent-run aggregate limit;
6. only after all checks pass, append audit execution and native `ToolResultMessage`;
7. continue to the next tool call or provider round.

Because all current Agent tools are read-only, an oversized later result cannot leave a mutation behind.

## Scope

- bounded tool-result serialization in the existing Agent service;
- focused service tests;
- no request/API schema expansion.

## Non-goals

- configurable budgets;
- token counting;
- result truncation/summarization;
- changing individual tool schemas;
- changing tool allowlist;
- retries with narrower arguments;
- write tools.

## Success criteria

- normal current tool calls are unaffected;
- a >24k serialized result fails before a follow-up provider round;
- several individually valid results exceeding 48k in one round fail;
- results accumulated across rounds cannot exceed 96k;
- oversized data is never sent as a partial/truncated tool message;
- caller cannot configure the limits;
- repository CI remains green.
