# Ramp-Rate Constraint Evaluation Implementation Plan

## File structure

- `apps/api/tests/test_scenario_constraints.py` — RED/GREEN ramp-rate behavior.
- `apps/api/src/hydropilot_api/services/scenario.py` — extend the conservative post-simulation evaluator.

## Task 1 — RED

Add tests proving:

1. a `m3/s/h` release ramp limit evaluates adjacent scenario states using actual elapsed minutes;
2. equality at the configured ramp limit is valid;
3. decreasing flow is checked by absolute rate magnitude;
4. an unsupported ramp unit is returned as unevaluated;
5. a conditional ramp constraint remains unevaluated;
6. no ramp evaluation changes scenario state values.

Expected state: supported ramp tests fail because all ramp-rate constraints are currently returned as unevaluated.

## Task 2 — GREEN

- add a private ramp-rate evaluator over ordered matching states;
- support only exact `<state unit>/h` constraint units;
- require at least two matching states;
- compute absolute adjacent change divided by elapsed hours;
- report violations at the later timestamp;
- preserve equality-at-bound behavior;
- return unsupported unit/time semantics as unevaluated rather than converting them.

Do not modify the simulation, release schedule, routing, or demo data.

## Task 3 — verification

- inspect the complete PR diff;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
