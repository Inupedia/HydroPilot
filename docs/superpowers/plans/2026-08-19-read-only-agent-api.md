# Read-Only Hydro Agent API Implementation Plan

## File structure

- `apps/api/src/hydropilot_api/agent.py` — reject extra request fields, prevalidate provider family, and classify loop-limit failure as deterministic Agent error.
- `apps/api/src/hydropilot_api/main.py` — add `/api/agent/chat` and explicit exception mapping.
- `apps/api/tests/test_agent.py` — update service-level provider/limit/request-hardening behavior.
- `apps/api/tests/test_agent_api.py` — RED/GREEN HTTP contract tests.

## Task 1 — RED request/service tests

Prove:

1. extra `tools` in `ReadOnlyAgentRequest` is rejected;
2. Anthropic/Gemini/Ollama Agent requests fail before provider network access;
3. tool-round exhaustion is a deterministic `ValueError`-family failure rather than `LLMProviderError`.

## Task 2 — RED endpoint tests

Prove:

1. a successful mocked Agent service response is returned from `POST /api/agent/chat`;
2. the endpoint passes the server repository to the Agent service;
3. `KeyError` -> 404;
4. `ValueError` and internal Pydantic `ValidationError` -> 422;
5. missing credential/base-url provider errors -> 400;
6. upstream provider failures -> 502;
7. request-body extras are rejected by FastAPI/Pydantic before service execution.

## Task 3 — GREEN service hardening

- set `ReadOnlyAgentRequest` model config to forbid extras;
- prevalidate adapter family against OpenAI-compatible support before the first provider call;
- raise `ValueError` for tool-round exhaustion;
- keep other provider failures as `LLMProviderError`.

## Task 4 — GREEN endpoint

- import Agent request/response/service into `main.py`;
- add `POST /api/agent/chat`;
- use `repo()` only;
- map deterministic Agent/tool errors, missing objects, credentials, and provider failures explicitly.

Do not change the Agent tool allowlist or add UI behavior.

## Task 5 — verification

- inspect complete diff;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
