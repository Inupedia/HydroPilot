# Scenario Validation HTTP Error Design

## Problem

The release scenario service now fails explicitly for unsupported or inconsistent model configuration, including missing routing parameters, branching/cyclic topology, ambiguous engineering curves, wrong units, and out-of-domain storage.

The FastAPI endpoint currently translates only missing objects (`KeyError`) to HTTP 404. Service-level `ValueError` exceptions escape as HTTP 500, incorrectly presenting a rejected scenario/configuration as a server failure.

## Goal

Translate deterministic scenario validation/configuration failures into HTTP 422 while preserving 404 for missing objects and leaving unexpected exceptions as 500.

## Design

In `/api/scenarios/release`:

- `KeyError` -> 404 `object not found` as today;
- `ValueError` -> 422 with the service error message as `detail`;
- all other exception types remain unhandled so genuine server faults are not disguised as user/configuration errors.

HTTP 422 matches FastAPI/Pydantic request-validation semantics and communicates that the request is syntactically valid but cannot be executed under the supplied model/data configuration.

## Scope

- release scenario API exception mapping;
- focused HTTP tests.

## Non-goals

- introducing a custom exception hierarchy;
- changing service validation rules;
- changing LLM endpoint error mapping;
- altering response schemas beyond existing FastAPI `detail` errors.

## Success criteria

- service `ValueError` maps to HTTP 422 with its message;
- missing reservoir remains HTTP 404;
- unexpected exceptions are not converted to 422;
- normal scenario requests remain HTTP 200;
- repository CI remains green.
