# Strict Hydro Tool Arguments Design

## Problem

HydroPilot validates model-proposed tool arguments with Pydantic, but the current argument models use Pydantic's default extra-field behavior. Unknown fields can therefore be silently ignored.

That creates two problems:

1. a malformed or adversarial tool call can contain fields that were never part of the tool contract yet still execute;
2. the Agent audit trace currently stores the model's raw argument dictionary, which can differ from the values that were actually validated/coerced/defaulted for execution.

For a grounded read-only Agent, the displayed audit trail should describe the effective execution contract, not merely echo the model proposal.

## Goal

Make every Hydro tool argument contract strict and make executed, normalized arguments first-class output of the tool execution boundary.

## Strict argument models

Add a shared internal base model:

`StrictToolArgs`

with:

`ConfigDict(extra="forbid")`

All five current argument models inherit it:

- `GetObjectArgs`
- `ListObjectsArgs`
- `TraceDownstreamArgs`
- `ListCurvesArgs`
- `ListConstraintsArgs`

Effects:

- unknown fields are rejected with Pydantic `ValidationError`;
- generated JSON schemas advertise that additional properties are not allowed;
- current coercion/default behavior for declared fields remains unchanged.

## Strict execution request

`HydroToolRequest` also forbids extra top-level fields. The only accepted request fields are:

- `name`
- `arguments`

This keeps `/api/tools/execute` consistent with the Agent's already-strict request boundary.

## Normalized execution arguments

Extend `HydroToolResponse` with:

`arguments: dict[str, Any]`

`execute_tool()` populates this from the validated argument model using JSON-mode serialization.

The normalized dictionary includes effective default values, for example:

- `trace_downstream` gets default `max_hops`, `offset`, and `limit` when omitted;
- `list_objects` gets default `offset`/`limit` and `object_type=null` when omitted.

This response therefore represents what the tool actually executed.

## Agent audit integration

`run_read_only_agent()` continues preserving the model's original call arguments inside the native assistant `tool_calls` history, because provider conversation history must reflect what the assistant actually emitted.

For the Agent's own audit trace, however, `AgentToolExecution.arguments` uses `tool_response.arguments` from the execution boundary.

Thus:

- provider protocol history = original model proposal;
- execution audit = validated effective arguments.

## Error behavior

Unknown tool arguments fail before handler execution.

The existing boundaries already map tool argument `ValidationError` to HTTP 422 for `/api/tools/execute` and `/api/agent/chat`.

No tool attempts to recover from unknown arguments or pass them back to the model.

## Scope

- strict tool argument/request validation;
- normalized effective arguments in `HydroToolResponse`;
- Agent audit trace uses normalized arguments;
- focused registry/API/Agent tests.

## Non-goals

- disabling Pydantic coercion for declared primitive values;
- changing tool capabilities;
- changing tool results;
- changing Agent allowlist;
- changing provider tool-call history;
- write tools.

## Success criteria

- every tool schema forbids extra properties;
- unknown tool argument fails before handler execution;
- unknown top-level `/api/tools/execute` field fails request validation;
- tool response exposes normalized/defaulted arguments;
- Agent audit trace reflects normalized executed arguments;
- provider-native assistant history still contains the model-proposed arguments;
- repository CI remains green.
