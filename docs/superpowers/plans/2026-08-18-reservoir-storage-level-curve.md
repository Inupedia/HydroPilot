# Reservoir Storage-Level Curve Implementation Plan

## File structure

- `packages/hydropilot-core/tests/test_reservoir.py` — RED/GREEN behavior for mass balance and storage-level interpolation.
- `packages/hydropilot-core/src/hydropilot_core/reservoir.py` — curve primitive and reservoir step integration.

## Task 1 — RED

Update reservoir tests first:

1. mass balance still produces the same storage but no longer fabricates a changed level without a curve;
2. a valid curve interpolates a midpoint correctly;
3. `step_reservoir` derives the post-step level from the supplied curve;
4. duplicate/decreasing storage or level points are rejected;
5. interpolation outside the curve domain is rejected;
6. existing storage/flow validation remains intact.

Expected state: tests fail because `StorageLevelPoint`, `StorageLevelCurve`, and the new step argument do not exist.

## Task 2 — GREEN

Implement only what the tests require:

- typed curve points;
- curve validation;
- piecewise-linear interpolation;
- optional curve input to `step_reservoir`;
- removal of the magic `* 50.0` level approximation.

Do not wire demo data or API scenarios in this PR.

## Task 3 — verification

- inspect the PR diff;
- run repository CI and native/visual checks;
- squash merge once required CI is green;
- allow the merged-branch cleanup workflow to remove the head branch and verify deletion.
