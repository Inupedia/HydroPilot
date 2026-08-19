# Explicit Reservoir Inflow Boundary Design

## Problem

The release scenario currently invents reservoir inflow as `release_cms * 0.6`. That makes storage evolution depend on an arbitrary relationship between a control decision (release) and an external boundary condition (inflow). The result is not auditable and prevents the scenario engine from consuming observed or forecast hydrographs later.

## Goal

Make reservoir inflow an explicit time-series boundary supplied to the scenario. The scenario engine must integrate that boundary into the 0D mass balance without inventing missing inflow values.

## Design

### Request contract

Add `HydrographPoint(timestamp_minutes, flow_cms)` and require `ReleaseScenarioRequest.inflow_hydrograph`.

Validation rules:

- at least two points;
- first point at minute 0;
- timestamps strictly increasing;
- flow values non-negative;
- the final point covers at least `duration_minutes`;
- `duration_minutes` must be divisible by `dt_minutes` so reservoir and Muskingum calculations share one fixed model time grid.

The request may use coarser timestamps than the simulation step. The scenario service linearly samples the hydrograph at each simulation timestamp.

### Reservoir integration

For each reservoir time interval, use the mean of the sampled inflow at the interval endpoints. This is trapezoidal integration of a piecewise-linear inflow boundary and maps cleanly onto the existing constant-flow `ReservoirStep` primitive.

The release remains constant in this PR. Dispatch schedules are a later concern.

### Traceability

Return reservoir `inflow` states alongside storage/level states so a scenario result records the boundary actually used.

### Studio behavior

The desktop demo adds an explicit `Reservoir inflow` field. For now it creates a constant two-point hydrograph spanning the 180-minute demo horizon. This is intentionally a user-visible scenario input, not a hidden model assumption. Future PRs can replace the manual value with observed/forecast data without changing the backend contract.

## Scope

- `apps/api/src/hydropilot_api/services/scenario.py`
- scenario/API tests
- `apps/studio/src/api/client.ts`
- `apps/studio/src/App.tsx`
- relevant Studio tests if required

## Non-goals

- rainfall-runoff modelling;
- observed/forecast data connectors;
- release schedules or optimization;
- storage-level fixture wiring;
- changing the Muskingum solver;
- operational flood-control recommendations.

## Success criteria

- `release_cms * 0.6` no longer exists;
- API requests without an inflow boundary are rejected;
- arbitrary valid inflow hydrographs are linearly sampled;
- reservoir storage responds to the supplied boundary through mass balance;
- scenario results expose the inflow series used;
- Studio sends an explicit inflow boundary;
- repository CI remains green.
