# Compact Object Inventory Tool Implementation Plan

## File structure

- `apps/api/src/hydropilot_api/tools.py` — inventory page models, paged args, compact mapping.
- `apps/api/tests/test_tools.py` — RED/GREEN page shape, filtering, pagination, and full-object regression.
- `apps/api/tests/test_tools_api.py` — real demo compact inventory response.

## Task 1 — RED

Prove:

1. `list_objects` returns a page with `offset`, `limit`, `total`, and compact items;
2. inventory items contain id/name/type/source but no geometry/properties;
3. default and explicit object-type filters still work;
4. offset/limit selects the expected deterministic slice;
5. offset beyond the end returns empty items with preserved total;
6. limit > 100 is rejected;
7. `get_object` still returns full geometry/properties;
8. real demo reservoir inventory has total 1 and one compact Shasta item.

## Task 2 — GREEN

- extend `ListObjectsArgs` with bounded `offset` and `limit`;
- add `ObjectInventoryItem` and `ObjectInventoryPage`;
- map repository objects to compact items;
- compute total before slicing;
- preserve repository ordering;
- leave `get_object` and repository protocol unchanged.

## Task 3 — verification

- inspect diff for Agent allowlist or unrelated API changes;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
