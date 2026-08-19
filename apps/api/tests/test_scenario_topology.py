import pytest

from hydropilot_api.domain import Geometry, HydroObject, HydroRelation, ObjectType, RelationType
from hydropilot_api.services import scenario as scenario_module
from hydropilot_api.services.scenario import HydrographPoint, ReleaseScenarioRequest, run_release_scenario


class MemoryHydroRepository:
    def __init__(self, objects: list[HydroObject], relations: list[HydroRelation]):
        self._objects = {item.id: item for item in objects}
        self._relations = relations

    def list_objects(self, object_type: ObjectType | None = None) -> list[HydroObject]:
        values = list(self._objects.values())
        if object_type is not None:
            values = [item for item in values if item.object_type is object_type]
        return values

    def get_object(self, object_id: str) -> HydroObject | None:
        return self._objects.get(object_id)

    def list_relations(self) -> list[HydroRelation]:
        return self._relations

    def list_curves(self, object_id=None, curve_type=None):
        return []


def reservoir() -> HydroObject:
    return HydroObject(
        id="reservoir-alpha",
        name="Reservoir Alpha",
        object_type=ObjectType.RESERVOIR,
        geometry=Geometry(type="Point", coordinates=[-122.0, 40.0]),
        properties={"initial_storage_m3": 1_000_000, "max_storage_m3": 2_000_000},
    )


def reach(object_id: str) -> HydroObject:
    return HydroObject(
        id=object_id,
        name=object_id,
        object_type=ObjectType.RIVER_REACH,
        geometry=Geometry(type="LineString", coordinates=[[-122.0, 40.0], [-121.9, 39.9]]),
        properties={"routing_k_minutes": 30, "routing_x": 0.2},
    )


def relation(relation_id: str, source_id: str, target_id: str, relation_type: RelationType) -> HydroRelation:
    return HydroRelation(
        id=relation_id,
        source_id=source_id,
        target_id=target_id,
        relation_type=relation_type,
    )


def request(*, max_hops: int = 4) -> ReleaseScenarioRequest:
    inflow = [
        HydrographPoint(timestamp_minutes=0, flow_cms=100),
        HydrographPoint(timestamp_minutes=60, flow_cms=100),
    ]
    release = [
        HydrographPoint(timestamp_minutes=0, flow_cms=50),
        HydrographPoint(timestamp_minutes=60, flow_cms=50),
    ]
    return ReleaseScenarioRequest(
        reservoir_id="reservoir-alpha",
        duration_minutes=60,
        dt_minutes=30,
        max_hops=max_hops,
        inflow_hydrograph=inflow,
        release_hydrograph=release,
    )


def test_release_scenario_rejects_branching_before_model_execution(monkeypatch):
    repo = MemoryHydroRepository(
        objects=[reservoir(), reach("receiving"), reach("branch-a"), reach("branch-b")],
        relations=[
            relation("discharge", "reservoir-alpha", "receiving", RelationType.DISCHARGES_TO),
            relation("flow-a", "receiving", "branch-a", RelationType.FLOWS_TO),
            relation("flow-b", "receiving", "branch-b", RelationType.FLOWS_TO),
        ],
    )
    calls = []

    def should_not_route(*args, **kwargs):
        calls.append((args, kwargs))
        return list(args[0])

    monkeypatch.setattr(scenario_module, "route_muskingum", should_not_route)

    with pytest.raises(ValueError, match="branching FLOWS_TO topology"):
        run_release_scenario(repo, request())

    assert calls == []


def test_release_scenario_rejects_cycle_before_model_execution(monkeypatch):
    repo = MemoryHydroRepository(
        objects=[reservoir(), reach("receiving"), reach("middle")],
        relations=[
            relation("discharge", "reservoir-alpha", "receiving", RelationType.DISCHARGES_TO),
            relation("flow-forward", "receiving", "middle", RelationType.FLOWS_TO),
            relation("flow-cycle", "middle", "receiving", RelationType.FLOWS_TO),
        ],
    )
    calls = []

    def should_not_route(*args, **kwargs):
        calls.append((args, kwargs))
        return list(args[0])

    monkeypatch.setattr(scenario_module, "route_muskingum", should_not_route)

    with pytest.raises(ValueError, match="cyclic FLOWS_TO topology"):
        run_release_scenario(repo, request())

    assert calls == []


def test_release_scenario_hop_limit_keeps_receiving_reach_and_one_descendant(monkeypatch):
    repo = MemoryHydroRepository(
        objects=[reservoir(), reach("receiving"), reach("next"), reach("beyond-limit")],
        relations=[
            relation("discharge", "reservoir-alpha", "receiving", RelationType.DISCHARGES_TO),
            relation("flow-1", "receiving", "next", RelationType.FLOWS_TO),
            relation("flow-2", "next", "beyond-limit", RelationType.FLOWS_TO),
        ],
    )
    calls = []

    def capture_route(inflow_cms, params, initial_outflow_cms=None):
        calls.append(list(inflow_cms))
        return list(inflow_cms)

    monkeypatch.setattr(scenario_module, "route_muskingum", capture_route)

    result = run_release_scenario(repo, request(max_hops=1))
    flow_objects = {state.object_id for state in result.states if state.variable == "flow"}

    assert flow_objects == {"receiving", "next"}
    assert len(calls) == 2
