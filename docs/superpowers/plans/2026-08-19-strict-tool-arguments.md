# Strict Hydro Tool Arguments Implementation Plan

## File structure

- `apps/api/src/hydropilot_api/tools.py` — strict argument/request base config and normalized execution arguments in responses.
- `apps/api/src/hydropilot_api/agent.py` — audit trace uses normalized tool-response arguments.
- `apps/api/tests/test_tools.py` — RED/GREEN schema, extra-field rejection, and normalized defaults.
- `apps/api/tests/test_tools_api.py` — HTTP 422 for unknown top-level/argument fields and normalized response arguments.
- `apps/api/tests/test_agent.py` — audit trace uses effective normalized arguments while provider history preserves model proposal.

## Task 1 — RED tool boundary

Prove:

1. every tool input schema has `additionalProperties=false`;
2. an extra argument on a known tool raises `ValidationError`;
3. an extra top-level field on `HydroToolRequest` raises `ValidationError`;
4. a normal execution response contains normalized arguments;
5. omitted defaults appear in normalized arguments.

## Task 2 — RED Agent audit

Prove:

1. model can omit optional/default tool fields;
2. provider-native assistant tool-call history still contains the original model proposal;
3. execution trace contains the normalized effective arguments including defaults;
4. extra model-proposed arguments stop the Agent before a follow-up provider round.

## Task 3 — GREEN

- add `StrictToolArgs` with `extra=forbid`;
- make every tool args model inherit it;
- set `HydroToolRequest` to `extra=forbid`;
- add `arguments` to `HydroToolResponse`;
- serialize validated args in JSON mode into the response;
- use `tool_response.arguments` in `AgentToolExecution`.

Do not change tool handlers, results, allowlist, or native assistant history.

## Task 4 — verification

- inspect diff for capability/result changes;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
