# Explicit Reservoir Storage Inputs Implementation Plan

## File structure

- `apps/api/src/hydropilot_api/services/scenario.py` — explicit reservoir storage input helper and removal of silent defaults.
- `apps/api/tests/test_scenario_reservoir_config.py` — RED/GREEN missing/invalid storage behavior.
- `apps/api/tests/test_api_objects.py` — existing real Sacramento scenario success remains authoritative.

## Task 1 — RED

Prove:

1. missing `initial_storage_m3` raises explicit `ValueError`;
2. missing `max_storage_m3` raises the same explicit required-input error;
3. non-numeric values raise explicit invalid-input error;
4. non-finite values are rejected;
5. valid explicit storage values continue into the existing scenario normally;
6. real Sacramento API scenario remains HTTP 200.

## Task 2 — GREEN

- add a private helper for required reservoir storage values;
- require both keys and reject nulls;
- convert to float and reject conversion errors/non-finite values;
- use the returned values to build the existing `ReservoirState`;
- remove the `0` and `max(storage, 1)` fallback expressions.

Do not change `initial_level_m`, curves, routing, constraints, hydrographs, or numeric fixture values.

## Task 3 — verification

- inspect diff to confirm silent defaults are gone and no new defaults were introduced;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
