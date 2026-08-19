# Studio Agent Grounding Trace Implementation Plan

## File structure

- `apps/studio/src/copilot/agent.ts` — display-message type, history normalization, grounding-label helper.
- `apps/studio/src/App.tsx` — retain Agent execution metadata and render the compact trace.
- `apps/studio/src/style.css` — small grounding-trace styles.
- `apps/studio/tests/agentCopilot.test.ts` — RED/GREEN history stripping and deterministic trace formatting.

## Task 1 — RED helper tests

Prove:

1. history entries containing display-only `toolExecutions`/`providerRounds` are normalized to `{role, content}` before Agent requests;
2. tool execution ordering is preserved by the display formatter;
3. argument keys are sorted deterministically;
4. nested/array argument values are compact JSON;
5. long argument values are truncated;
6. zero-argument calls format as the tool name only.

## Task 2 — GREEN helper/model

- define a Studio display message type extending the UI's role/content shape with optional execution metadata;
- normalize outgoing history instead of spreading UI message objects;
- add deterministic compact execution-label helper.

## Task 3 — GREEN App/UI

- store `response.tool_executions` and `response.provider_rounds` on the assistant display message;
- render `Grounded by` only when executions exist;
- preserve execution order;
- render compact tool/argument labels;
- leave text-only answers unchanged.

## Task 4 — styling

- add compact muted grounding label/chip styles within the existing Copilot thread;
- do not expand the panel or add a modal.

## Task 5 — verification

- inspect diff for accidental backend/Agent behavior changes;
- require React tests/build and repository CI to pass;
- squash merge;
- verify merged branch deletion.
