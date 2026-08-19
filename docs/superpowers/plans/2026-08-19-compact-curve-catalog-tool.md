# Compact Curve Catalog Tool Implementation Plan

## File structure

- `apps/api/src/hydropilot_api/tools.py` — paged curve args and compact catalog result models.
- `apps/api/tests/test_tools.py` — RED/GREEN compact shape, pagination, filtering, and full repository/direct behavior regression.
- `apps/api/tests/test_tools_api.py` — real demo empty compact curve page.
- `apps/api/tests/test_api_curves.py` — existing direct full-curve API remains authoritative and unchanged.
- `apps/api/tests/test_scenario_curves.py` — existing scenario full-curve behavior remains authoritative and unchanged.

## Task 1 — RED

Prove:

1. tool `list_curves` returns page metadata and compact curve items;
2. compact items contain `point_count` but no `points`;
3. typed `curve_type` filtering still works;
4. offset/limit pagination is deterministic;
5. limit > 50 is rejected;
6. real demo reservoir returns an empty compact page;
7. existing direct object-curves API still returns full point arrays;
8. existing scenario curve tests continue unchanged.

## Task 2 — GREEN

- extend `ListCurvesArgs` with bounded offset/limit;
- add `CurveInventoryItem` and `CurveInventoryPage`;
- compact repository curve records after filtering and slicing;
- preserve existing object-existence validation;
- do not modify repository, direct curve API, or scenario code.

## Task 3 — verification

- inspect diff for Agent allowlist/scenario/data changes;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
