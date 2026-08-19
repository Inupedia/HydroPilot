import pytest
from hydropilot_api.domain import HydroRelation, RelationType
from hydropilot_api.topology import downstream_path


def relation(source: str, target: str) -> HydroRelation:
    return HydroRelation(id=f"{source}-{target}", source_id=source, target_id=target, relation_type=RelationType.FLOWS_TO)


def branching_relations() -> list[HydroRelation]:
    return [
        relation("A", "C"),
        relation("A", "B"),
        relation("B", "E"),
        relation("B", "D"),
        relation("C", "F"),
        relation("C", "E"),
    ]


def test_downstream_path_is_deterministic_and_hop_aware():
    result = downstream_path(
        "A",
        [relation("A", "C"), relation("A", "B"), relation("B", "D"), relation("C", "D")],
        max_hops=3,
    )
    assert [(item.object_id, item.hop) for item in result] == [("B", 1), ("C", 1), ("D", 2)]


def test_downstream_path_protects_against_cycles():
    result = downstream_path("A", [relation("A", "B"), relation("B", "A")], max_hops=10)
    assert [(item.object_id, item.hop) for item in result] == [("B", 1)]


def test_downstream_path_optional_result_bound_preserves_bfs_prefix():
    full = downstream_path("A", branching_relations(), max_hops=3)
    bounded = downstream_path("A", branching_relations(), max_hops=3, max_results=3)

    assert [(item.object_id, item.hop) for item in full] == [
        ("B", 1),
        ("C", 1),
        ("D", 2),
        ("E", 2),
        ("F", 2),
    ]
    assert [(item.object_id, item.hop) for item in bounded] == [
        ("B", 1),
        ("C", 1),
        ("D", 2),
    ]


def test_downstream_path_zero_result_bound_returns_empty():
    assert downstream_path("A", branching_relations(), max_hops=3, max_results=0) == []


def test_downstream_path_rejects_negative_bounds():
    with pytest.raises(ValueError):
        downstream_path("A", [], max_hops=-1)
    with pytest.raises(ValueError):
        downstream_path("A", [], max_results=-1)
