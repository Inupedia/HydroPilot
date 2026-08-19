# Compact Curve Catalog Tool Design

## Problem

The read-only `list_curves` Agent tool currently returns complete `HydroCurve` records, including every curve point. A detailed engineering curve may contain hundreds or thousands of points, while an inventory question such as “what curves are configured?” needs only metadata.

The backend scenario service and direct object-curves API legitimately need full curve data, but the Agent catalog path should not bulk-load points into model context.

## Goal

Make `list_curves` a bounded compact catalog while leaving repository curve storage, scenario execution, and the direct `/api/objects/{object_id}/curves` API unchanged.

## Arguments

`ListCurvesArgs`:

- `object_id: str`
- `curve_type: CurveType | None = None`
- `offset: int = 0`, minimum 0
- `limit: int = 20`, minimum 1, maximum 50

The tool still verifies that `object_id` exists before listing curves.

## Result

Return `CurveInventoryPage`:

- `offset`
- `limit`
- `total`
- `items`

Each `CurveInventoryItem` contains:

- `id`
- `object_id`
- `curve_type`
- `x_unit`
- `y_unit`
- `point_count`
- `source`

The `points` array is intentionally excluded.

## Execution

1. verify the object exists using the existing object-specific tool boundary;
2. call `repo.list_curves(object_id=..., curve_type=...)`;
3. preserve repository ordering;
4. compute total matching curves;
5. apply offset/limit slicing;
6. map selected curves to compact metadata items.

An offset past the end returns an empty page with the correct total.

## Compatibility boundary

Unchanged full-curve paths:

- repository `list_curves()` contract;
- `GET /api/objects/{object_id}/curves`;
- release scenario storage-level curve adapter.

Only the Hydro tool result shape changes.

## Non-goals

- adding a full-curve Agent tool;
- curve-point sampling/interpolation endpoints;
- repository/database pagination;
- curve mutation;
- changing engineering data;
- changing Agent allowlist.

## Success criteria

- Agent `list_curves` results contain no `points` field;
- point count remains visible;
- type filtering remains typed and deterministic;
- default page size is 20 and hard maximum is 50;
- direct object-curves API continues returning full points;
- scenario curve use remains unchanged;
- repository CI remains green.
