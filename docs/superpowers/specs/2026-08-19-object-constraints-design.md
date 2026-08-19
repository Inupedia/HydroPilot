# Object Operating-Constraints Repository and API Design

## Problem

HydroPilot already defines typed `HydroConstraint` records for minimum, maximum, range, and ramp-rate limits, but those records cannot currently be stored in the fixture repository or queried through the API. A future dispatch engine or Agent therefore has no stable way to discover operating limits attached to an engineering object.

## Goal

Make operating constraints first-class read-only repository resources and expose them for one HydroObject through the API, without interpreting or enforcing them yet.

## Design

### Repository contract

Extend `HydroRepository` with:

`list_constraints(object_id: str | None = None, variable: str | None = None) -> list[HydroConstraint]`

The fixture repository parses an optional top-level `constraints` array. Existing fixtures without that key remain valid and expose an empty list.

Filtering:

- optional `object_id`;
- optional exact `variable` string;
- deterministic ordering by constraint id.

### API

Add:

`GET /api/objects/{object_id}/constraints`

Optional query parameter:

`variable: str | None`

Behavior:

- missing object -> 404 `object not found`;
- existing object with no constraints -> 200 `[]`;
- existing object with constraints -> typed `HydroConstraint` list;
- variable filter delegates to the repository.

Return the domain representation unchanged, including `constraint_type`, bounds, unit, `active_when`, and source.

### Semantics boundary

This PR does not decide whether a constraint is hard/soft, whether `active_when` is true, or whether a scenario violates it. Those decisions belong in a dedicated constraint-evaluation layer.

## Scope

- repository protocol;
- fixture parsing/querying;
- one read-only API endpoint;
- focused tests.

## Non-goals

- adding Sacramento/Shasta constraints;
- enforcing constraints;
- dispatch optimization;
- rule evaluation;
- UI rendering;
- persistence migration;
- mutation endpoints.

## Success criteria

- existing Sacramento fixture exposes no invented constraints;
- a fixture/test repository can store and filter typed constraints;
- API returns bounds, unit, active condition, and provenance unchanged;
- missing objects return 404;
- repository CI remains green.
