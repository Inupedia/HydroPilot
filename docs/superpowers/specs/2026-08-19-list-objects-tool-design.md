# List Objects Hydro Tool Design

## Problem

The read-only Agent can fetch a known object, trace downstream topology, and inspect curves/constraints, but it cannot discover the repository's object inventory. Studio now offers a read-only prompt asking what engineering objects exist, so the model should not guess ids or infer the inventory from scene counts.

## Goal

Add one typed read-only Hydro tool:

`list_objects`

with optional `object_type` filtering using the existing `ObjectType` enum.

## Contract

Arguments:

- `object_type: ObjectType | None = None`

Behavior:

- no filter -> `repo.list_objects()`;
- filter -> `repo.list_objects(object_type)`;
- return repository objects unchanged through the existing JSON-safe tool response conversion;
- repository ordering remains authoritative/deterministic.

The tool does not require an object id and therefore never raises the missing-object `KeyError` used by object-specific tools.

## Agent exposure

Add `list_objects` explicitly to `READ_ONLY_AGENT_TOOL_NAMES`.

The allowlist remains explicit; this is an intentional expansion from four to five read-only tools, not automatic registry inheritance.

## API exposure

No new HTTP route is required. Existing `/api/tools` and `/api/tools/execute` automatically expose and execute registered tools, and `/api/agent/chat` automatically receives the updated allowlisted Agent definitions.

## Non-goals

- full-text search;
- fuzzy name matching;
- pagination;
- spatial filtering;
- mutation;
- scenario execution;
- additional Agent tools.

## Success criteria

- registry catalog includes `list_objects` as read-only;
- no-filter call returns all test/demo objects;
- typed `object_type` filter works;
- invalid object type is rejected by Pydantic;
- real `/api/tools/execute` can list demo reservoir objects;
- Agent advertises the new tool and still excludes scenario/write tools;
- repository CI remains green.
