# Object Engineering-Curves API Design

## Problem

HydroPilot repositories can now store and query typed engineering curves, and the release scenario consumes reservoir level-storage curves internally. That data is still invisible at the API boundary. Future Studio panels and Agent tools should not depend directly on fixture/repository implementation details to inspect engineering relationships.

## Goal

Expose repository-backed engineering curves for one HydroObject through a small read-only API endpoint with optional type filtering.

## Design

Add:

`GET /api/objects/{object_id}/curves`

Optional query parameter:

`curve_type: CurveType | None`

Behavior:

- missing object -> HTTP 404 `object not found`;
- existing object with no curves -> HTTP 200 `[]`;
- existing object with curves -> HTTP 200 list of typed `HydroCurve` records;
- `curve_type` filters through the repository contract and uses the existing enum validation;
- ordering is repository-deterministic (fixture repository sorts by curve id).

The endpoint returns the domain `HydroCurve` representation unchanged, including units, points, curve type, and source/provenance field. It does not transform level-storage curves into solver orientation.

## Scope

- one read-only FastAPI endpoint;
- focused API tests.

## Non-goals

- curve creation/update/deletion;
- UI rendering;
- curve interpolation endpoint;
- solver conversion;
- adding engineering values to the Sacramento fixture;
- pagination/version selection.

## Success criteria

- Sacramento reservoir honestly returns an empty curve list;
- a repository-backed curve can be returned through the endpoint with units/source intact;
- type filtering is forwarded correctly;
- missing objects return 404;
- repository CI remains green.
