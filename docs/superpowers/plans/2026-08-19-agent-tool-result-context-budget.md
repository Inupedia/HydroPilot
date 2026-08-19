# Agent Tool-Result Context Budget Implementation Plan

## File structure

- `apps/api/src/hydropilot_api/agent.py` — fixed budget constants, deterministic serialization, per-result/round/run checks.
- `apps/api/tests/test_agent_result_budget.py` — RED/GREEN oversized-result and aggregate-budget behavior.
- `apps/api/tests/test_agent.py` — existing normal Agent regression coverage remains authoritative.

## Task 1 — RED

Prove:

1. existing normal `get_object` execution remains unchanged through existing Agent tests;
2. one tool result over 24,000 serialized characters raises `ValueError` before a second provider request;
3. multiple results each under 24,000 but together over 48,000 in one round raise before follow-up;
4. results accumulated across multiple tool rounds cannot exceed 96,000;
5. oversized results are not truncated or sent as tool messages;
6. `ReadOnlyAgentRequest` exposes no budget override field.

## Task 2 — GREEN

- add fixed per-result, per-round, and total-run character constants;
- extract deterministic tool-result JSON serialization helper;
- measure the exact serialized content used for `ToolResultMessage`;
- enforce prospective budgets before appending execution/history;
- keep existing allowlist and tool execution behavior unchanged.

## Task 3 — verification

- inspect diff for request-schema/allowlist changes;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
