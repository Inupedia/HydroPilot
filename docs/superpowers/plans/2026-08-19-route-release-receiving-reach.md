# Release Receiving-Reach Routing Implementation Plan

## File structure

- `apps/api/tests/test_scenario.py` — RED/GREEN behavior proving hop-0 routing.
- `apps/api/tests/test_api_objects.py` — API result expectations for the receiving reach.
- `apps/api/src/hydropilot_api/services/scenario.py` — prepend the receiving reach to the routed sequence.

## Task 1 — RED

Add tests proving:

1. the `DISCHARGES_TO` target is passed through Muskingum before its descendants;
2. the receiving reach's own K/X values are used;
3. flow result states include the receiving reach;
4. missing routing properties on the receiving reach fail explicitly.

Expected state: tests fail because the current routing loop starts with descendants returned by `downstream_path()`.

## Task 2 — GREEN

- build the routed sequence from the receiving reach plus existing downstream path;
- use the existing `_routing_parameters` helper for every reach including hop 0;
- preserve current sequential propagation and result shape.

Do not modify `downstream_path()` or add branching behavior in this PR.

## Task 3 — verification

- inspect full PR diff;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
