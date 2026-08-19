# Paged Constraint Catalog Tool Implementation Plan

## File structure

- `apps/api/src/hydropilot_api/tools.py` — paged constraint args/result wrapper.
- `apps/api/tests/test_tools.py` — RED/GREEN pagination, variable filter, semantic-field preservation, and limit validation.
- `apps/api/tests/test_tools_api.py` — real demo empty constraint page.
- `apps/api/tests/test_agent.py` — existing native Agent tool-result regression updated to the paged constraint result shape.
- `apps/api/tests/test_api_constraints.py` — existing direct full-list constraint API remains authoritative and unchanged.
- `apps/api/tests/test_scenario_constraints.py` — existing scenario evaluation remains authoritative and unchanged.

## Task 1 — RED

Prove:

1. tool `list_constraints` returns `offset`, `limit`, `total`, and full constraint items;
2. semantic fields including bounds, `active_when`, and `source` are preserved;
3. variable filtering still works;
4. offset/limit pagination is deterministic;
5. offset beyond the end returns an empty page with preserved total;
6. limit > 100 is rejected;
7. real demo reservoir returns an empty paged constraint result;
8. Agent native tool-result history uses the new page shape;
9. direct object-constraints API and scenario constraint tests remain unchanged.

## Task 2 — GREEN

- extend `ListConstraintsArgs` with bounded `offset` and `limit`;
- add `ConstraintInventoryPage` containing full `HydroConstraint` items;
- paginate only after repository filtering;
- preserve object-existence validation and repository ordering;
- align the existing Agent result-shape regression;
- do not modify repository, direct API, scenario evaluator, or Agent allowlist.

## Task 3 — verification

- inspect diff for semantic-field loss or unrelated behavior changes;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
