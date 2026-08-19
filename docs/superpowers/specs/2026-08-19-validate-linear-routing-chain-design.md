# Linear Routing-Chain Validation Design

## Problem

The release scenario uses one sequential Muskingum series: the outflow from one routed reach becomes the inflow to the next. The topology helper `downstream_path()` is broader than that model: it performs graph traversal and may return multiple descendants from a branching network.

If a `FLOWS_TO` node has two outgoing targets, treating the traversal result as a sequence would incorrectly route the full flow through branch A and then through branch B. Cycles are similarly unsuitable for this one-pass solver.

## Goal

Make the current solver contract explicit and safe: a release scenario may route only a single, acyclic downstream chain. Branching or cyclic `FLOWS_TO` topology must fail before model execution rather than being silently serialized.

## Design

### Scenario-specific chain resolution

Replace use of generic `downstream_path()` inside the release scenario with a small chain resolver that:

1. starts at the reservoir's `DISCHARGES_TO` target;
2. includes that receiving reach as hop 0;
3. examines outgoing `FLOWS_TO` relations at each step;
4. stops when there is no downstream target or `max_hops` descendants have been added;
5. follows exactly one downstream target when present;
6. raises a configuration error when more than one downstream target exists;
7. raises a configuration error if a target would revisit an already-seen object.

Targets are deduplicated before cardinality checks so duplicate relation records do not masquerade as a physical branch.

### Scope boundary

This is intentionally validation, not branch simulation. Correct branch/diversion routing requires split ratios, lateral inflows, junction mass balance, and potentially different solvers. HydroPilot should reject unsupported physics instead of inventing it.

The public `/api/network/{id}/downstream` endpoint keeps its existing generic graph-traversal behavior. Only release-scenario routing adopts the stricter chain contract.

## Scope

- release scenario chain resolution and tests;
- no UI changes.

## Non-goals

- flow splitting;
- junction solvers;
- tributary/lateral inflows;
- diversion rules;
- changing the generic topology API;
- graph database changes.

## Success criteria

- current linear Sacramento fixture continues to run;
- a branching `FLOWS_TO` graph fails explicitly before Muskingum execution;
- a cyclic graph fails explicitly;
- the receiving reach remains the first routed object;
- `max_hops` continues to count descendants after hop 0;
- repository CI remains green.
