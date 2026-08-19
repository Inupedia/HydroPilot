# Object Operating-Constraints Implementation Plan

## File structure

- `apps/api/src/hydropilot_api/repositories/protocols.py` — add constraint query contract.
- `apps/api/src/hydropilot_api/repositories/fixture.py` — parse optional constraints and filter them.
- `apps/api/src/hydropilot_api/main.py` — read-only object-constraints endpoint.
- `apps/api/tests/test_fixture_constraints.py` — prove existing no-constraint fixture compatibility and fixture filtering.
- `apps/api/tests/test_api_constraints.py` — prove HTTP behavior and provenance preservation.

## Task 1 — RED repository tests

Prove:

1. Sacramento exposes `[]` constraints;
2. fixture constraints parse into `HydroConstraint`;
3. object and variable filtering work.

## Task 2 — RED API tests

Prove:

1. existing Sacramento reservoir returns `[]`;
2. a test repository returns typed constraints unchanged;
3. variable filtering is forwarded;
4. missing objects return 404.

Expected state: tests fail because the repository and API have no constraint contract.

## Task 3 — GREEN

- extend `HydroRepository`;
- parse `data.get("constraints", [])`;
- implement deterministic filtering;
- add `GET /api/objects/{object_id}/constraints`.

No scenario code calls `list_constraints` in this PR, so scenario test repositories do not need compatibility shims yet.

Do not enforce constraints or modify demo data.

## Task 4 — verification

- inspect diff for data or scenario-behavior changes;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
