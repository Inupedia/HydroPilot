# Model Property Provenance Implementation Plan

## File structure

- `apps/api/src/hydropilot_api/domain.py` — typed property origin/provenance and additive HydroObject metadata.
- `data/demo/sacramento_v0_1.json` — annotate solver-driving properties only; do not change numeric values.
- `apps/api/tests/test_fixture_provenance.py` — RED/GREEN solver-property provenance coverage.
- `apps/api/tests/test_api_objects.py` — verify detailed object API exposes provenance while existing behavior remains intact.
- `apps/api/tests/test_tools.py` / existing compact inventory tests — compact list_objects shape remains authoritative and unchanged.

## Task 1 — RED domain/fixture tests

Prove:

1. `PropertyProvenance` accepts the three typed origins and rejects unknown origins;
2. every demo reservoir scenario-driving property that exists has a matching provenance entry;
3. every demo reach with `routing_k_minutes` / `routing_x` has matching provenance;
4. current demo K/X provenance is `model_assumption` with an explicit uncalibrated/non-operational note;
5. current reservoir scenario-driving provenance is `model_assumption` with an explicit validation/non-operational note;
6. the current numeric property values remain parseable and unchanged by the domain extension.

## Task 2 — RED API visibility

Prove:

1. detailed `GET /api/objects/reservoir-shasta` returns property-level provenance;
2. compact `list_objects` tool continues returning only id/name/type/source.

## Task 3 — GREEN domain

- add `PropertyValueOrigin` enum;
- add `PropertyProvenance` model;
- add default-empty `property_provenance` to `HydroObject`.

## Task 4 — GREEN fixture annotations

- add provenance entries for current reservoir `initial_storage_m3`, `max_storage_m3`, and `initial_level_m` when present;
- add provenance for every reach `routing_k_minutes` and `routing_x`;
- classify current values conservatively as `model_assumption`;
- use explicit notes saying current routing values are uncalibrated demonstrator parameters and reservoir values require authoritative validation before operational use;
- do not edit any numeric property value.

## Task 5 — verification

- inspect JSON diff to confirm provenance-only additions;
- verify scenario/core behavior is unchanged through existing tests;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
