# Linear Routing-Chain Validation Implementation Plan

## File structure

- `apps/api/tests/test_scenario_topology.py` — RED/GREEN behavior for branching, cycles, and hop limits.
- `apps/api/tests/test_scenario.py` — existing linear-order regression coverage remains authoritative.
- `apps/api/src/hydropilot_api/services/scenario.py` — scenario-specific chain resolver.

## Task 1 — RED

Add tests proving:

1. a branch from the receiving reach raises before `route_muskingum` is called;
2. a downstream cycle raises before repeated routing;
3. the existing linear chain preserves receiving-reach-first order;
4. `max_hops` limits descendants while keeping hop 0.

Expected state: branch tests fail because generic BFS descendants are currently serialized into one Muskingum chain.

## Task 2 — GREEN

- add a private scenario chain resolver over `FLOWS_TO` relations;
- include the receiving reach;
- follow only one unique target at each hop;
- reject branching and cycles explicitly;
- stop after `max_hops` descendants;
- replace scenario use of `downstream_path()` with the new resolver.

Do not change the public topology helper or API.

## Task 3 — verification

- inspect the full PR diff;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
