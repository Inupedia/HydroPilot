# Read-Only Hydro Agent Loop Implementation Plan

## File structure

- `apps/api/src/hydropilot_api/agent.py` — bounded orchestration models, allowlist, tool conversion, and Agent loop.
- `apps/api/tests/test_agent.py` — RED/GREEN provider/tool orchestration and safety-boundary tests.

## Task 1 — RED core loop tests

Add tests proving:

1. a text-only first provider round returns immediately with zero tool executions;
2. `get_object` is proposed by the model, executed through the Hydro registry, fed back as a native tool result, and followed by final text;
3. multiple read-only calls in one provider round preserve call ids and execution order;
4. only the fixed four read-only Hydro tools are advertised to the model;
5. a non-allowlisted tool proposal fails before execution or a second provider call;
6. caller-provided `system` and `tool` roles are rejected;
7. `max_tool_rounds` prevents an unbounded tool loop;
8. the Agent audit trace contains call id, name, arguments, and result.

## Task 2 — GREEN models and tool boundary

- add `ReadOnlyAgentRequest`, inheriting provider/model/credential/generation fields from `ChatRequest`;
- validate caller message roles to `user`/`assistant` only;
- add capped `max_tool_rounds`;
- add `AgentToolExecution` and `ReadOnlyAgentResponse`;
- define the fixed four-tool Agent allowlist;
- convert allowlisted `HydroToolDefinition` records to `FunctionToolDefinition` records;
- prepend the fixed read-only Agent system prompt.

## Task 3 — GREEN orchestration

- call `tool_chat_round()` using the fixed function-tool list;
- return immediately on text-only response;
- before every tool-containing round, enforce the round cap;
- reject non-allowlisted calls;
- append native assistant tool-call history;
- execute calls sequentially through `execute_tool()`;
- serialize tool results deterministically to JSON and append matching `ToolResultMessage` records;
- accumulate the execution trace;
- allow one final provider round after the last permitted tool round.

Do not add an HTTP endpoint, write tools, or scenario execution in this PR.

## Task 4 — verification

- inspect complete PR diff for any registry or scenario expansion;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
