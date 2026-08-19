# Release Hydrograph Schedule Implementation Plan

## File structure

- `apps/api/tests/test_scenario.py` — RED/GREEN behavior for release schedule validation, reservoir integration, and routing initialization.
- `apps/api/tests/test_api_objects.py` — HTTP contract update from scalar release to release hydrograph.
- `apps/api/src/hydropilot_api/services/scenario.py` — release hydrograph sampling/integration and steady-start routing.
- `apps/studio/src/api/client.ts` — send release and inflow hydrographs explicitly.
- `apps/studio/src/App.tsx` — construct the constant demo release hydrograph from the visible release field.

## Task 1 — RED

Add tests proving:

1. `release_hydrograph` is required and follows the same structural validation as inflow;
2. a time-varying release is linearly sampled on the model grid;
3. reservoir storage uses interval-mean release rather than a scalar release;
4. result states expose sampled release values;
5. Muskingum receives the sampled release series and initializes from its first value rather than `release * 0.35`;
6. HTTP tests use the new contract.

Expected state: tests fail because the request still requires scalar `release_cms` and downstream routing still uses the 0.35 multiplier.

## Task 2 — GREEN backend

- replace scalar `release_cms` with `release_hydrograph`;
- share hydrograph validation for inflow/release;
- sample release on the scenario time grid;
- trapezoidally integrate interval release in `ReservoirStep`;
- add `release` result states;
- route the sampled release series;
- initialize each reach with its own first input flow.

## Task 3 — GREEN Studio

- change `hydroApi.releaseScenario` to accept inflow and release hydrographs;
- build a constant release hydrograph from the existing visible release field;
- keep the current simple release UI unchanged.

## Task 4 — verification

- inspect full PR diff;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
