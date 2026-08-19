# Explicit Reservoir Storage Inputs Design

## Problem

The release scenario currently reads reservoir state using silent fallbacks:

- missing `initial_storage_m3` -> `0`;
- missing `max_storage_m3` -> `max(initial_storage, 1)`.

These defaults let an incomplete repository produce plausible-looking model output from invented storage values. That is the same class of hidden assumption HydroPilot has been removing from inflow, release, routing, and engineering-curve behavior.

## Goal

Require explicit stored reservoir values for:

- `initial_storage_m3`;
- `max_storage_m3`.

If either is absent or cannot be interpreted as a finite numeric model input, fail before simulation instead of inventing a value.

`initial_level_m` remains optional because level can be unavailable or derived from a storage-level curve.

## Validation

Add a small scenario helper that:

1. checks both required property keys are present and non-null;
2. converts both to floats;
3. rejects non-numeric or non-finite values with an explicit configuration error;
4. returns the two values to the existing `ReservoirState` model.

`ReservoirState` remains authoritative for physical state bounds already encoded there, including:

- storage >= 0;
- max storage > 0;
- storage <= max storage.

Do not duplicate those checks in the scenario helper.

## Error semantics

Missing values:

`reservoir <id> requires initial_storage_m3 and max_storage_m3`

Invalid numeric values:

`reservoir <id> has invalid initial_storage_m3 or max_storage_m3`

The existing API boundary maps these deterministic `ValueError` failures to HTTP 422.

## Compatibility boundary

The Sacramento demo already contains both values, so its scenario output should remain numerically unchanged.

No fixture value, routing parameter, hydrograph behavior, curve behavior, or constraint behavior changes.

## Scope

- release scenario reservoir initialization;
- focused service/API regression tests.

## Non-goals

- requiring `initial_level_m`;
- replacing current demo values;
- changing provenance classifications;
- changing reservoir equations;
- adding current/live reservoir observations;
- operational model calibration.

## Success criteria

- missing initial storage fails explicitly;
- missing maximum storage fails explicitly;
- invalid/non-finite storage configuration fails explicitly;
- real Sacramento scenario still succeeds with unchanged expected behavior;
- no silent reservoir storage defaults remain in scenario code;
- repository CI remains green.
