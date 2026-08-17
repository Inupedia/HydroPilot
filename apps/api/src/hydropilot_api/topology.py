from __future__ import annotations

from collections import defaultdict, deque
from .domain import HydroRelation, NetworkPathItem, RelationType


def downstream_path(
    start_id: str,
    relations: list[HydroRelation],
    *,
    max_hops: int = 8,
) -> list[NetworkPathItem]:
    if max_hops < 0:
        raise ValueError("max_hops must be non-negative")

    adjacency: dict[str, list[str]] = defaultdict(list)
    for relation in relations:
        if relation.relation_type == RelationType.FLOWS_TO:
            adjacency[relation.source_id].append(relation.target_id)
    for targets in adjacency.values():
        targets.sort()

    visited: set[str] = {start_id}
    queue: deque[tuple[str, int]] = deque([(start_id, 0)])
    result: list[NetworkPathItem] = []

    while queue:
        current, hop = queue.popleft()
        if hop >= max_hops:
            continue
        for target in adjacency.get(current, []):
            if target in visited:
                continue
            visited.add(target)
            item = NetworkPathItem(object_id=target, hop=hop + 1)
            result.append(item)
            queue.append((target, hop + 1))

    return result
