# Read-Only Hydro Agent API Design

## Problem

HydroPilot now has a tested bounded read-only Agent service, but it is not reachable through the API. Before exposing it, the service/request boundary also needs HTTP-appropriate semantics:

- caller-supplied unknown fields such as a fake `tools` list should be rejected instead of silently ignored;
- selecting a provider family that cannot perform native tool calling should be a request/executionability error, not an upstream gateway failure;
- exhausting the Agent tool-round budget should be a bounded-Agent error, not an upstream provider outage.

## Goal

Expose the existing bounded read-only Agent through:

`POST /api/agent/chat`

with explicit request validation and stable HTTP error mapping.

## Request hardening

`ReadOnlyAgentRequest` forbids extra fields. This makes attempts to supply fields such as `tools` fail Pydantic validation instead of being ignored.

Caller message-role validation remains unchanged: only `user` and `assistant` history is accepted.

Before any provider network access, the Agent validates that the chosen provider uses the OpenAI-compatible adapter family currently supported by `tool_chat_round()`.

Unsupported provider family raises `ValueError` with an Agent-specific message.

The tool-round limit also raises `ValueError` because it is a deterministic bounded-Agent execution condition rather than an upstream LLM transport/protocol failure.

## Endpoint

Add:

`POST /api/agent/chat`

Request model:

`ReadOnlyAgentRequest`

Response model:

`ReadOnlyAgentResponse`

The endpoint always uses the server-selected Hydro repository returned by `repo()`; the caller cannot select or inject a repository.

## HTTP error mapping

- request-body Pydantic validation -> FastAPI 422;
- missing Hydro object raised by a tool (`KeyError`) -> 404;
- Agent/tool deterministic errors (`ValueError` or internal Pydantic `ValidationError`) -> 422;
- missing API key/base URL (`LLMProviderError` containing `required`) -> 400, matching the existing LLM endpoint;
- upstream LLM HTTP/protocol failures (`LLMProviderError`) -> 502.

Unexpected exception types remain unhandled so genuine server failures are not disguised.

## Scope

- request hardening in the existing Agent service;
- one read-only Agent HTTP endpoint;
- focused service/API tests.

## Non-goals

- Studio integration;
- write tools;
- scenario/release tools;
- streaming;
- auth/session redesign;
- persistent Agent memory;
- non-OpenAI-compatible native tool protocols.

## Success criteria

- successful Agent service result is returned by `/api/agent/chat` unchanged;
- endpoint uses the server repository;
- caller-supplied `tools` is rejected with 422;
- unsupported provider family is rejected before network access with 422;
- tool-round exhaustion maps to 422;
- missing object maps to 404;
- missing credentials map to 400;
- upstream provider failures map to 502;
- repository CI remains green.
