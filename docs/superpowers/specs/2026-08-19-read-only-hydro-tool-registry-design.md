# Read-Only Hydro Tool Registry Design

## Problem

HydroPilot's Copilot can call chat providers, but map/model actions are still selected by frontend regexes. There is no backend tool catalog with machine-readable input schemas, no single execution boundary, and no stable contract an LLM agent can use to discover water-network capabilities.

Connecting an LLM directly to arbitrary API routes would make validation, auditing, and future safety controls inconsistent.

## Goal

Create a backend registry of small, typed, read-only Hydro tools with JSON Schema definitions and a unified execution API. This establishes the tool layer an Agent can use later without giving the LLM write/model-execution authority in the same change.

## Initial tool set

Expose four read-only tools:

1. `get_object`
   - input: `object_id`
   - result: one `HydroObject`
2. `trace_downstream`
   - input: `object_id`, optional `max_hops`
   - result: `NetworkPathItem[]`
3. `list_curves`
   - input: `object_id`, optional `curve_type`
   - result: `HydroCurve[]`
4. `list_constraints`
   - input: `object_id`, optional `variable`
   - result: `HydroConstraint[]`

All four verify the target object exists and fail with `KeyError` when it does not.

## Registry model

Each tool has a `HydroToolDefinition` containing:

- stable name;
- concise description;
- `input_schema` generated from a Pydantic argument model;
- `read_only=True`.

Tool input schemas are generated from the same Pydantic models used for runtime validation, preventing documentation/execution drift.

## Execution model

`HydroToolRequest` contains:

- `name`;
- `arguments` object.

The registry:

1. resolves the tool by exact name;
2. validates arguments with the tool's Pydantic model;
3. invokes the registered handler against `HydroRepository`;
4. returns a JSON-serializable result.

Unknown tool names fail explicitly. Invalid arguments remain validation errors rather than being coerced by custom parsing.

## API boundary

Add:

- `GET /api/tools` -> tool catalog;
- `POST /api/tools/execute` -> execute one read-only tool.

HTTP mapping:

- missing object (`KeyError`) -> 404;
- unknown tool / tool validation or configuration errors -> 422;
- unexpected failures remain 500.

## Safety boundary

This first registry is deliberately read-only. It does not expose scenario execution, release changes, data mutation, shell access, arbitrary SQL, or arbitrary HTTP requests.

A later PR may register `run_release_scenario` as an explicitly classified model-execution tool with separate approval/safety semantics.

## Scope

- new backend tool-registry module;
- catalog and execution endpoints;
- focused registry/API tests.

## Non-goals

- LLM tool calling;
- LangGraph orchestration;
- write/action tools;
- scenario execution as a tool;
- frontend changes;
- tool permissions/authentication;
- arbitrary database queries.

## Success criteria

- catalog exposes all four tools and valid JSON schemas;
- runtime validation uses the same argument models represented by those schemas;
- tools return existing repository/domain representations unchanged;
- missing objects and invalid tools map to explicit HTTP errors;
- no write/model-execution capability is exposed;
- repository CI remains green.
