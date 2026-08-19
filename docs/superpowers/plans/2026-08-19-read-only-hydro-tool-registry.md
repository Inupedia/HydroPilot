# Read-Only Hydro Tool Registry Implementation Plan

## File structure

- `apps/api/src/hydropilot_api/tools.py` — typed tool definitions, argument models, registry, and handlers.
- `apps/api/src/hydropilot_api/main.py` — catalog and execution endpoints plus HTTP error mapping.
- `apps/api/tests/test_tools.py` — RED/GREEN registry catalog, validation, execution, and read-only classification.
- `apps/api/tests/test_tools_api.py` — RED/GREEN HTTP behavior.

## Task 1 — RED registry tests

Prove:

1. catalog contains exactly the four initial read-only tools;
2. every definition exposes a JSON object input schema generated from its argument model;
3. `get_object` returns the requested domain object;
4. `trace_downstream` forwards hop limits;
5. curve/constraint tools preserve repository filtering;
6. unknown tool names and invalid arguments fail explicitly;
7. missing objects raise `KeyError`.

## Task 2 — GREEN registry

Implement:

- Pydantic input models per tool;
- `HydroToolDefinition`, `HydroToolRequest`, `HydroToolResponse`;
- stable handler registry;
- catalog generation from the same argument models used at runtime;
- read-only handlers over `HydroRepository` and existing topology logic.

Do not add scenario execution or generic request/database tools.

## Task 3 — RED/GREEN API

Add tests then endpoints:

- `GET /api/tools`;
- `POST /api/tools/execute`.

Map missing objects to 404 and tool/argument errors to 422. Do not broadly catch unexpected exceptions.

## Task 4 — verification

- inspect catalog/diff for accidental action tools;
- confirm no Studio, scenario, fixture-data, or LLM-provider behavior changes;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
