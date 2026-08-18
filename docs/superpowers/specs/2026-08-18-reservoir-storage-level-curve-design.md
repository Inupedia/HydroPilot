# Reservoir Storage-Level Curve Design

## Problem

The current reservoir step model updates water level using an arbitrary proportional rule: storage change divided by maximum storage, multiplied by 50 metres. That produces a visually changing level but has no engineering meaning and can misrepresent reservoir behavior.

## Goal

Keep the existing 0D mass-balance model, but make level calculation depend on an explicit storage-level relationship. When no relationship is available, the model must not invent a new level.

## Design

### Storage-level relationship

Add two core types in `hydropilot_core.reservoir`:

- `StorageLevelPoint(storage_m3, level_m)`
- `StorageLevelCurve(points)`

The curve is piecewise linear. It is a solver input, not a HydroPilot persistence model.

Validation rules:

- at least two points;
- storage values strictly increase;
- level values strictly increase.

`level_for_storage(storage_m3)` linearly interpolates between adjacent points. Values outside the curve domain are rejected rather than extrapolated.

### Reservoir stepping

Extend `step_reservoir` with an optional `storage_level_curve` argument.

- Mass balance and storage clamping remain unchanged.
- With a curve, the returned level is interpolated from the resulting storage.
- Without a curve, a storage-changing step returns `level_m=None`; HydroPilot must not fabricate a level from a magic coefficient.
- If storage does not change, an already-known level may be preserved.

## Scope

- modify `packages/hydropilot-core/src/hydropilot_core/reservoir.py`;
- update reservoir core tests.

## Non-goals

- fixture/data changes;
- API scenario wiring;
- level-area or discharge curves;
- gate/outlet capacity;
- dispatch rules or optimization;
- persistence.

Those are separate PRs so this solver primitive remains independently testable.

## Success criteria

- the 0D mass balance remains numerically unchanged;
- the old `storage_ratio_delta * 50.0` behavior no longer exists;
- piecewise-linear level interpolation is tested;
- invalid and out-of-domain curves fail explicitly;
- the full repository CI remains green.
