# Studio Read-Only Agent Integration Implementation Plan

## File structure

- `apps/studio/src/api/client.ts` — typed Agent request/response and `/api/agent/chat` client.
- `apps/studio/src/copilot/agent.ts` — compatible-provider filtering and read-only message construction.
- `apps/studio/src/App.tsx` — route free-text Copilot through the Agent and update UX copy.
- `apps/studio/tests/agentCopilot.test.ts` — RED/GREEN provider/message helpers and Agent API client tests.
- remove `apps/studio/src/copilot/commands.ts` and `apps/studio/tests/copilotCommands.test.ts`.

## Task 1 — RED helpers/client

Prove:

1. only `openai-compatible` providers are eligible for Copilot;
2. Agent message construction emits only `user`/`assistant` roles;
3. Studio state is included as descriptive read-only context;
4. context explicitly says scenario controls are unavailable to the Agent;
5. `hydroApi.agentChat()` posts to `/api/agent/chat`;
6. the request does not contain a `tools` field.

## Task 2 — GREEN client/helper

- add Agent request/response types and `agentChat` to the API client;
- add provider filtering helper;
- add read-only context/message builder.

## Task 3 — GREEN App migration

- remove `parseCopilotCommand` import/use;
- replace action-oriented quick prompts with read-only questions;
- select only Agent-compatible providers;
- replace `hydroApi.llmChat()` with `hydroApi.agentChat()`;
- never send a system/tool message from Studio;
- update Copilot heading, initial guidance, placeholder, and provider helper copy;
- leave explicit highlight/scenario buttons and functions unchanged.

## Task 4 — cleanup

- delete obsolete regex command parser;
- delete obsolete parser tests;
- keep generic `/api/llm/chat` client support available for future non-Agent features, but do not use it in Copilot.

## Task 5 — verification

- inspect diff to ensure scenario execution remains button-only;
- require React tests/build and repository CI to pass;
- squash merge;
- verify merged branch deletion.
