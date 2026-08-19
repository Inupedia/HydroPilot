# Object Engineering-Curves API Implementation Plan

## File structure

- `apps/api/tests/test_api_curves.py` — RED/GREEN HTTP tests with both the real demo repository and a test repository containing curves.
- `apps/api/src/hydropilot_api/main.py` — read-only object-curves route.

## Task 1 — RED

Add tests proving:

1. the existing Sacramento reservoir returns `[]` rather than synthetic curve data;
2. a repository-provided curve is returned with id/type/units/points/source intact;
3. `curve_type` is forwarded as a typed filter;
4. a missing object returns HTTP 404.

Expected state: tests fail because the route does not exist.

## Task 2 — GREEN

- import `CurveType` and `HydroCurve` into the API module;
- add `GET /api/objects/{object_id}/curves` with `response_model=list[HydroCurve]`;
- verify object existence before querying curves;
- delegate filtering to `repo().list_curves(...)`.

Do not add mutation or UI behavior.

## Task 3 — verification

- inspect the complete diff;
- confirm demo fixture data is unchanged;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
