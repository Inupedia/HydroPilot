# Storage-Level Curve Wiring Implementation Plan

## File structure

- `apps/api/src/hydropilot_api/repositories/protocols.py` — add curve query contract.
- `apps/api/src/hydropilot_api/repositories/fixture.py` — parse optional curves and filter them.
- `apps/api/src/hydropilot_api/services/scenario.py` — adapt domain level-storage curve to the core solver.
- `apps/api/tests/test_fixture.py` — prove old fixtures remain valid and curve filtering works.
- `apps/api/tests/test_scenario_curves.py` — prove reservoir level follows repository engineering data and invalid curve configurations fail.
- `apps/api/tests/test_scenario.py` — update the existing in-memory repository to satisfy the expanded contract.
- `apps/api/tests/test_scenario_topology.py` — update the topology test repository to satisfy the expanded contract.

## Task 1 — RED repository tests

Add tests proving:

1. an existing fixture without `curves` exposes an empty list;
2. a fixture with curves parses `HydroCurve` records;
3. filters by object id and curve type work.

## Task 2 — RED scenario tests

Add tests proving:

1. a valid level-storage curve determines the initial level from initial storage;
2. subsequent storage changes produce interpolated level states;
3. wrong curve units fail explicitly;
4. more than one level-storage curve fails explicitly;
5. storage outside the curve domain fails rather than extrapolating.

Expected state: tests fail because repositories have no curve contract and scenarios never pass a curve into `step_reservoir`.

## Task 3 — GREEN repository

- extend the repository protocol;
- parse `data.get("curves", [])` in the fixture repository;
- implement deterministic curve filtering/sorting.

Do not modify the Sacramento fixture data.

## Task 4 — GREEN scenario adapter

- select zero or one `LEVEL_STORAGE` curve for the reservoir;
- require `m` / `m3` units;
- reverse domain `(level, storage)` points into core `(storage, level)` points;
- derive initial level from the curve when present;
- pass the adapted curve to every reservoir step.

## Task 5 — verification

- inspect the full PR diff and confirm no engineering curve values were added to demo data;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
