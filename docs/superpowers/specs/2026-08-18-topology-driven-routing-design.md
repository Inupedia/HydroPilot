# Topology-Driven Release Routing Design

## Problem

The release scenario currently contains two synthetic assumptions even though the demo hydrograph already carries the required information:

- routing always starts from the literal object id `reach-001` instead of following the reservoir's `DISCHARGES_TO` relationship;
- Muskingum `K` and `X` are generated from downstream hop index instead of using each river reach's `routing_k_minutes` and `routing_x` properties.

This makes scenario behavior depend on code layout rather than the water-network model and prevents the same scenario engine from being reused with a different basin fixture.

## Goal

Make release routing derive its path and Muskingum parameters from repository data. The scenario runner should not invent a starting reach or routing coefficients when the hydrograph already defines them.

## Design

### Release-path resolution

For the requested reservoir, find exactly one outgoing `DISCHARGES_TO` relation. Its target is the first river reach receiving the reservoir release. Downstream traversal starts from that object rather than a hard-coded id.

A missing or ambiguous discharge relation is a scenario configuration error rather than a reason to silently fall back to a demo id.

### Per-reach routing parameters

For each downstream reach, read:

- `routing_k_minutes`
- `routing_x`

Convert `routing_k_minutes` to seconds and construct the existing `MuskingumParameters`. The current stability validation remains authoritative. Missing or invalid properties should fail explicitly; the scenario runner must not synthesize replacement parameters.

### Compatibility

The current Sacramento fixture already has one `reservoir-shasta -> reach-001` `DISCHARGES_TO` relation and routing properties on its river reaches, so the existing public demo flow remains supported while becoming data-driven.

## Scope

- update `apps/api/src/hydropilot_api/services/scenario.py`;
- add focused scenario service tests.

## Non-goals

- replacing the synthetic reservoir inflow assumption;
- storage-level curve fixture wiring;
- dynamic rainfall/runoff forecasting;
- model calibration;
- changing the Muskingum solver itself;
- UI changes.

## Success criteria

- a release scenario can run on a graph whose reach ids are not `reach-001`, `reach-002`, etc.;
- the routing call receives each reach's stored K/X values;
- missing topology or routing configuration fails explicitly;
- existing API and core tests remain green.
