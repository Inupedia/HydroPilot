# Topology-Driven Release Routing Implementation Plan

## File structure

- `apps/api/tests/test_scenario.py` — focused service tests using an in-memory hydrograph.
- `apps/api/src/hydropilot_api/services/scenario.py` — topology resolution and per-reach Muskingum parameter loading.

## Task 1 — RED

Add tests that prove:

1. the release path starts from the reservoir's `DISCHARGES_TO` relation, even when custom reach ids are used;
2. the Muskingum call receives K/X from the downstream reach properties;
3. missing or ambiguous `DISCHARGES_TO` topology fails explicitly;
4. missing routing K/X fails explicitly.

Expected state: the custom graph test fails because the implementation still looks for `reach-001` and synthesizes routing parameters from hop count.

## Task 2 — GREEN

Modify only the scenario service:

- resolve the release receiving reach from relations;
- load each routed reach from the repository;
- read `routing_k_minutes` and `routing_x`;
- construct the existing `MuskingumParameters` without fallback values;
- remove the hop-based synthetic K/X logic.

Keep the existing release hydrograph and reservoir inflow assumptions unchanged for this PR.

## Task 3 — verification

- inspect the complete diff;
- require repository CI to pass;
- squash merge;
- verify the cleanup workflow removes the merged branch.
