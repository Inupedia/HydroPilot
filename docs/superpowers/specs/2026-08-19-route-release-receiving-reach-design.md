# Release Receiving-Reach Routing Design

## Problem

A reservoir release enters the river network through the target of its `DISCHARGES_TO` relation. The scenario engine currently uses that target only as the starting node for `downstream_path()`. Because `downstream_path()` returns descendants and excludes the start object, the receiving reach itself is never routed and never receives flow result states.

For the Sacramento fixture this means the release enters `reach-001`, but Muskingum routing begins at `reach-002`. Travel time and attenuation for the first reach are therefore omitted.

## Goal

Treat the reservoir's discharge target as the first routed river reach (hop 0), then route its descendants in downstream order exactly as before.

## Design

### Routed reach sequence

Resolve exactly one `DISCHARGES_TO` target as today. Build the routed sequence as:

1. receiving reach at hop 0;
2. objects returned by `downstream_path(receiving_reach, ..., max_hops=...)`.

The existing `max_hops` meaning remains unchanged: it limits graph hops after the receiving reach. Therefore `max_hops=0` would mean only the receiving reach, although the current request contract still requires at least 1 and is not changed by this PR.

### Model parameters

The receiving reach must satisfy the same routing configuration requirements as every other routed reach: `routing_k_minutes` and `routing_x` must exist and pass `MuskingumParameters` validation. No special default is allowed.

### Results

The receiving reach gets `flow` states at every scenario timestamp. Its routed output then becomes the input to the next downstream reach.

## Scope

- scenario routing service;
- focused scenario/API tests.

## Non-goals

- changing `downstream_path()` semantics;
- branching-network routing;
- tributary inflows;
- diversion splitting;
- model calibration;
- UI changes.

## Success criteria

- the `DISCHARGES_TO` target is routed first;
- its stored K/X values are used;
- its flow states appear in scenario results;
- existing downstream reaches continue to route sequentially;
- repository CI remains green.
