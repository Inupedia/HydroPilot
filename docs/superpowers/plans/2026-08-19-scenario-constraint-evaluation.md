# Scenario Constraint Evaluation Implementation Plan

## File structure

- `apps/api/src/hydropilot_api/services/scenario.py` — result models and conservative post-simulation evaluator.
- `apps/api/tests/test_scenario_constraints.py` — RED/GREEN supported, skipped, and unit-safety behavior.
- existing scenario test repositories — add empty `list_constraints()` shims because scenario execution will now query constraints.
- `apps/api/tests/test_api_objects.py` — verify real Sacramento response exposes empty evaluation lists.

## Task 1 — RED

Add tests proving:

1. unconditional maximum/minimum/range constraints report only out-of-bound timestamps;
2. equality at configured bounds passes;
3. conditional constraints are returned as unevaluated;
4. ramp-rate constraints are returned as unevaluated;
5. a constraint whose variable is absent from scenario states is returned as unevaluated;
6. unit mismatch raises `ValueError`;
7. real Sacramento scenario returns empty `violations` and `unevaluated_constraints`.

Expected state: tests fail because scenario responses do not evaluate repository constraints.

## Task 2 — GREEN models/evaluator

- add `ConstraintViolation` and `UnevaluatedConstraint` response models;
- add default-empty evaluation fields to `ReleaseScenarioResponse`;
- implement a private evaluator over completed states and repository constraints;
- support only unconditional MINIMUM/MAXIMUM/RANGE comparisons;
- reject unit mismatch;
- explicitly mark conditional, ramp-rate, and missing-variable constraints unevaluated.

## Task 3 — GREEN integration

- call the evaluator after all reservoir/river states are produced;
- return evaluation results without modifying model states;
- add empty `list_constraints` methods to existing in-memory scenario test repositories.

## Task 4 — verification

- inspect diff for accidental enforcement or demo-data changes;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
