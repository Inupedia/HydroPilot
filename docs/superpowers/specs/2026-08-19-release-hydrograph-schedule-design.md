# Release Hydrograph Schedule Design

## Problem

The release scenario still treats reservoir release as one constant scalar and initializes downstream Muskingum routing with `release * 0.35`. Both assumptions are demo shortcuts: real dispatch changes through time, and the river model should not invent a pre-scenario flow from an arbitrary percentage of the release decision.

## Goal

Represent release as an explicit time-series control schedule and use a documented steady-start convention for river routing. Reservoir storage and downstream flow should both respond to the supplied release hydrograph.

## Design

### Request contract

Replace scalar `release_cms` with required `release_hydrograph: list[HydrographPoint]`.

Both inflow and release hydrographs follow the same rules:

- at least two points;
- first point at minute 0;
- timestamps strictly increasing;
- non-negative flow;
- final point covers the scenario duration.

The existing fixed simulation time grid remains authoritative and both hydrographs are linearly sampled onto it.

### Reservoir mass balance

For every interval, compute:

- mean interval inflow from the two sampled inflow endpoints;
- mean interval release from the two sampled release endpoints.

Pass those values to the existing 0D `ReservoirStep`. This is trapezoidal integration of piecewise-linear boundary/control curves.

### Result traceability

Return reservoir `release` states alongside `inflow`, `storage`, and any available `level` states so each scenario result records the exact control schedule used.

### River routing initialization

Route the sampled release series downstream. For each Muskingum reach, initialize outflow at the first input flow value for that reach. This is a steady-start convention at t=0 and removes the arbitrary `release * 0.35` factor.

Future work may replace this convention with persisted pre-scenario river states, but this PR must not invent an unrelated multiplier.

### Studio behavior

Keep the current visible `Reservoir release` scalar field as a simple demo control. Studio converts that visible value into a constant two-point release hydrograph over the 180-minute horizon. This preserves the simple UI while the backend contract becomes schedule-capable.

## Scope

- scenario request/service and tests;
- API tests;
- Studio API client and scenario call wiring.

## Non-goals

- optimized release generation;
- rule evaluation;
- gate/outlet capacity constraints;
- observed pre-scenario river-state persistence;
- multi-reservoir coordinated dispatch;
- UI editor for arbitrary release curves.

## Success criteria

- scalar `release_cms` is removed from the backend scenario contract;
- `release * 0.35` no longer exists;
- time-varying release schedules alter reservoir storage correctly;
- sampled release values are returned as result states;
- Muskingum receives the sampled release series and a steady-start initial condition;
- Studio still runs a constant-release demo by explicitly constructing a hydrograph;
- repository CI remains green.
