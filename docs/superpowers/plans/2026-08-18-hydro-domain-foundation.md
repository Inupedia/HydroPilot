# Hydro Domain Foundation Implementation Plan

## File structure

- `apps/api/tests/test_domain.py` — executable acceptance tests for vocabulary and validation behavior.
- `apps/api/src/hydropilot_api/domain.py` — additive domain types and validators only.

## Task 1 — RED: encode required behavior in tests

Create domain tests that prove:

1. new water-network asset types are accepted by `HydroObject`;
2. new operational relationship types are accepted by `HydroRelation`;
3. a valid level-storage curve is accepted;
4. curves with fewer than two points or non-increasing x values are rejected;
5. min/max/range/ramp constraints validate their required bounds;
6. a range with inverted bounds is rejected;
7. an operating rule preserves priority, condition, and action payloads.

Expected state: the new test module fails to import the new symbols.

## Task 2 — GREEN: implement the smallest typed domain extension

Modify only `domain.py`:

- extend `ObjectType` and `RelationType` additively;
- introduce `CurveType`, `HydroCurvePoint`, and `HydroCurve`;
- introduce `ConstraintType` and `HydroConstraint` with structural validation;
- introduce `HydroRule`.

Do not add interpolation, persistence, evaluation, API routes, or UI behavior.

Expected state: new tests pass and existing tests remain compatible.

## Task 3 — verification and review

- inspect the complete PR diff for accidental subsystem changes;
- verify CI status for the PR head commit;
- require green checks before merge;
- squash-merge the PR;
- rely on the repository's `Cleanup merged branches` workflow to delete the merged head branch.
