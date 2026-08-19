# Bounded Downstream Trace Tool Design

## Problem

The read-only `trace_downstream` tool limits graph depth with `max_hops <= 25`, but depth does not bound result cardinality. A branching `FLOWS_TO` graph can contain many nodes at each hop, so one Agent tool call may still return a large traversal result.

The generic `downstream_path()` helper currently performs deterministic breadth-first traversal and returns all reachable descendants up to the hop limit. The public network API relies on that behavior and should remain unchanged by default.

## Goal

Add a bounded paged Agent trace without changing existing public topology semantics.

- preserve deterministic breadth-first order;
- add optional early-stop support to `downstream_path()`;
- make the Agent tool request only enough traversal items to serve one page plus one look-ahead item;
- return `has_more` instead of computing a potentially expensive full total.

## Topology helper extension

Extend:

`downstream_path(start_id, relations, *, max_hops=8, max_results: int | None = None)`

Rules:

- `None` preserves current full traversal behavior;
- non-negative integer bounds the number of returned `NetworkPathItem` values;
- `max_results=0` returns an empty list immediately;
- BFS ordering, cycle protection, target sorting, hop numbering, and relation filtering remain unchanged;
- traversal stops as soon as the requested number of unique descendants has been appended.

The public `/api/network/{id}/downstream` endpoint continues calling without `max_results`, so its contract is unchanged.

## Tool arguments

`TraceDownstreamArgs`:

- `object_id: str`
- `max_hops: int = 8`, range 0..25
- `offset: int = 0`, minimum 0
- `limit: int = 100`, range 1..200

## Tool result

Return `DownstreamTracePage`:

- `offset`
- `limit`
- `has_more`
- `items: list[NetworkPathItem]`

No `total` is returned because obtaining the exact total would defeat early stopping on large graphs.

## Execution

1. verify the starting object exists;
2. calculate `needed = offset + limit + 1`;
3. call `downstream_path(..., max_results=needed)`;
4. page items from `[offset : offset + limit]`;
5. set `has_more = len(result) > offset + limit`;
6. return only the selected page.

An offset beyond all reachable results returns `items=[]` and `has_more=false`. This may require traversing up to `offset + limit + 1`, but the tool still has bounded request parameters and never materializes beyond the look-ahead bound.

## Compatibility boundary

Unchanged:

- public `/api/network/{object_id}/downstream` response remains a plain full list up to `max_hops`;
- release scenario uses its own strict linear-chain resolver and is unaffected;
- Agent allowlist remains unchanged.

## Non-goals

- exact total count;
- changing graph semantics;
- branch flow simulation;
- database-native graph pagination;
- spatial filtering;
- mutation;
- scenario changes.

## Success criteria

- Agent trace result is bounded by default 100 / maximum 200;
- page ordering matches existing BFS order;
- `has_more` is accurate via one-item look-ahead;
- topology helper can early-stop without changing unbounded calls;
- public downstream API tests remain unchanged and pass;
- scenario routing remains unchanged;
- repository CI remains green.
