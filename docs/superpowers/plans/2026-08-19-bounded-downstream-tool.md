# Bounded Downstream Trace Tool Implementation Plan

## File structure

- `apps/api/src/hydropilot_api/topology.py` — optional deterministic BFS result cap.
- `apps/api/src/hydropilot_api/tools.py` — paged trace args/result and bounded look-ahead execution.
- `apps/api/tests/test_topology.py` — RED/GREEN early-stop behavior without changing unbounded traversal.
- `apps/api/tests/test_tools.py` — RED/GREEN trace page, ordering, `has_more`, and limit validation.
- `apps/api/tests/test_tools_api.py` — real demo bounded trace tool coverage.
- existing `/api/network/.../downstream` tests remain unchanged and authoritative.

## Task 1 — RED topology helper

Prove:

1. unbounded calls preserve existing BFS results;
2. `max_results=0` returns empty;
3. a small `max_results` returns the first N existing BFS items in the same order;
4. negative `max_results` is rejected.

## Task 2 — RED tool contract

Prove:

1. `trace_downstream` returns `{offset, limit, has_more, items}`;
2. default page preserves current BFS order;
3. explicit pages use one-item look-ahead for accurate `has_more`;
4. offset beyond results returns empty items and `has_more=false`;
5. limit > 200 is rejected;
6. real demo trace is bounded and paged;
7. public downstream API remains a plain list.

## Task 3 — GREEN

- add optional `max_results` to `downstream_path()`;
- early-return for zero and reject negative values;
- stop BFS immediately after the requested count is appended;
- add `offset`/`limit` to `TraceDownstreamArgs`;
- add `DownstreamTracePage`;
- request only `offset + limit + 1` items from topology;
- preserve object-existence validation.

Do not change public API invocation, scenario routing, or Agent allowlist.

## Task 4 — verification

- inspect diff for public topology/scenario behavior changes;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
