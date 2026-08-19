# Explicit Reservoir Inflow Boundary Implementation Plan

## File structure

- `apps/api/tests/test_scenario.py` — RED/GREEN behavior for hydrograph validation, sampling, and reservoir integration.
- `apps/api/tests/test_api_objects.py` — API contract compatibility for the required boundary.
- `apps/api/src/hydropilot_api/services/scenario.py` — typed hydrograph boundary and sampling/integration.
- `apps/studio/src/api/client.ts` — send an explicit demo hydrograph.
- `apps/studio/src/App.tsx` — expose inflow as a scenario input.

## Task 1 — RED

Add tests proving:

1. a request requires at least two inflow points covering the scenario horizon;
2. timestamps must start at zero and strictly increase;
3. linear sampling produces expected intermediate flows;
4. reservoir storage uses the supplied hydrograph rather than any function of release;
5. result states include the sampled inflow series;
6. the HTTP scenario test sends the new required boundary.

Expected state: tests fail because the request has no inflow hydrograph contract and the service still computes `release_cms * 0.6`.

## Task 2 — GREEN backend

Implement only the required boundary behavior:

- `HydrographPoint`;
- request validation;
- piecewise-linear sampling helper;
- trapezoidal interval inflow passed to `ReservoirStep`;
- `inflow` result states;
- remove `release_cms * 0.6`.

Do not add forecast providers or dispatch schedules.

## Task 3 — GREEN Studio

- extend `hydroApi.releaseScenario` to accept an inflow value and send a two-point constant hydrograph for the demo horizon;
- add a visible inflow input to the release scenario panel;
- include inflow in scenario status text.

## Task 4 — verification

- inspect the complete diff for scope creep;
- require repository CI to pass;
- squash merge;
- verify the cleanup workflow removes the merged head branch.