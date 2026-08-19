# Paged Constraint Catalog Tool Design

## Problem

The read-only `list_constraints` Agent tool still returns every matching `HydroConstraint` in one response. Individual constraints are relatively compact, but real operating rulebooks can attach many limits to one reservoir, outlet, gate, or control point.

Unlike object geometry or curve point arrays, the fields on one constraint are semantically important to the Agent: variable, type, unit, bounds, activation condition, and provenance should remain visible. The safe improvement is therefore bounded pagination rather than projection/removal.

## Goal

Make `list_constraints` a bounded paged catalog while preserving complete constraint metadata for each returned item.

The repository contract, direct `/api/objects/{object_id}/constraints` endpoint, and scenario constraint evaluation remain unchanged and continue to use complete constraint lists.

## Arguments

`ListConstraintsArgs`:

- `object_id: str`
- `variable: str | None = None`
- `offset: int = 0`, minimum 0
- `limit: int = 50`, minimum 1, maximum 100

The object must still exist before constraints are queried.

## Result

Return `ConstraintInventoryPage`:

- `offset`
- `limit`
- `total`
- `items`

Each item preserves the full existing `HydroConstraint` domain representation:

- `id`
- `object_id`
- `variable`
- `constraint_type`
- `unit`
- `min_value`
- `max_value`
- `active_when`
- `source`

No semantic field is removed or transformed.

## Execution

1. verify object existence;
2. call `repo.list_constraints(object_id=..., variable=...)`;
3. preserve repository ordering;
4. compute total before slicing;
5. apply offset/limit;
6. return the selected full constraint records inside the typed page.

Offset beyond the end is a valid empty page with preserved total.

## Compatibility boundary

Unchanged full-list consumers:

- repository `list_constraints()`;
- `GET /api/objects/{object_id}/constraints`;
- release scenario constraint evaluator.

Only the Hydro tool result shape changes.

## Non-goals

- constraint projection/removal of fields;
- repository/database pagination;
- filtering by constraint type or active condition;
- rule evaluation changes;
- mutation;
- Agent allowlist changes;
- new operating data.

## Success criteria

- tool results are bounded by default 50 / maximum 100;
- variable filtering remains deterministic;
- every returned constraint keeps full semantic fields and provenance;
- offset/limit pagination works;
- direct object-constraints API remains an unpaged full list;
- scenario constraint evaluation remains unchanged;
- repository CI remains green.
