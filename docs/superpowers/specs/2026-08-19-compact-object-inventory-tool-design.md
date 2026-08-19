# Compact Object Inventory Tool Design

## Problem

The newly added `list_objects` read-only tool delegates directly to `repo.list_objects()` and returns full `HydroObject` records. Those records may contain line/polygon geometry and arbitrary properties. That is useful for a single object but wasteful and potentially very large for an inventory query.

A production water network may contain hundreds or thousands of objects. Feeding complete geometry/properties for every object into an LLM tool result would consume context unnecessarily and make inventory discovery fragile.

## Goal

Make `list_objects` a bounded catalog/discovery tool rather than a bulk object export.

- return compact object summaries only;
- support typed object filtering;
- support bounded offset/limit pagination;
- expose total matching count so the Agent knows whether another page exists;
- keep `get_object` as the path to a complete object record.

## Arguments

`ListObjectsArgs`:

- `object_type: ObjectType | None = None`
- `offset: int = 0`, minimum 0
- `limit: int = 50`, minimum 1, maximum 100

The pagination cap is an Agent/tool-result safety boundary, not a repository storage limit.

## Result

Return a typed page:

`ObjectInventoryPage`

- `offset`
- `limit`
- `total`
- `items`

Each `ObjectInventoryItem` contains only:

- `id`
- `name`
- `object_type`
- `source`

Geometry and `properties` are intentionally excluded.

## Execution

1. call `repo.list_objects(object_type)` using the existing repository contract;
2. preserve repository ordering;
3. compute `total` before slicing;
4. slice `[offset : offset + limit]`;
5. map the selected objects to compact inventory items;
6. return the typed page through the existing JSON-safe tool response.

An offset beyond the end returns an empty `items` list with the same `total`; this is a valid page, not an error.

## Compatibility boundary

`/api/objects` and `get_object` remain unchanged and continue returning full object records.

Only the `list_objects` tool result shape changes. The tool was introduced specifically as an Agent inventory primitive, so tightening it before broader external adoption is preferable to carrying an unbounded bulk-data contract forward.

## Non-goals

- repository-level database pagination;
- fuzzy/full-text search;
- spatial filtering;
- sorting controls;
- geometry/property projection options;
- mutation;
- changing `get_object`.

## Success criteria

- `list_objects` result contains no geometry or properties;
- default page is capped at 50 and hard limit at 100;
- object-type filter still works;
- offset/limit pagination is deterministic;
- total count is available;
- full `get_object` behavior is unchanged;
- Agent allowlist does not expand;
- repository CI remains green.
