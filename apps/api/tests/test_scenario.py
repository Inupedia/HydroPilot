import pytest
from pydantic import ValidationError

from hydropilot_api.domain import (
    Geometry,
    HydroObject,
    HydroRelation,
    ObjectType,
    RelationType,
)
from hydropilot_api.services import scenario as scenario_module
from hydropilot_api.services.scenario import (
    HydrographPoint,
    ReleaseScenarioRequest,
    run_release_scenario,
)


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


def point() -> Geometry:
    return Geometry(type="Point", coordinates=[-122.0, 40.0])


def line() -> Geometry:
    return Geometry(type="LineString", coordinates=[[-122.0, 40.0], [-121.9, 39.9]])


def reservoir() -> HydroObject:
    return HydroObject(
        id="reservoir-alpha",
        name="Reservoir Alpha",
        object_type=ObjectType.RESERVOIR,
        geometry=point(),
        properties={"initial_storage_m3": 1_000_000, "max_storage_m3": 2_000_000},
    )


def reach(object_id: str, *, k_minutes: float | None = None, x: float | None = None) -> HydroObject:
    properties = {}
    if k_minutes is not None:
        properties["routing_k_minutes"] = k_minutes
    if x is not None:
        properties["routing_x"] = x
    return HydroObject(
        id=object_id,
        name=object_id,
        object_type=ObjectType.RIVER_REACH,
        geometry=line(),
        properties=properties,
    )


def relation(
    relation_id: str,
    source_id: str,
    target_id: str,
    relation_type: RelationType,
) -> HydroRelation:
    return HydroRelation(
        id=relation_id,
        source_id=source_id,
        target_id=target_id,
        relation_type=relation_type,
    )


def constant_boundary(flow_cms: float, duration_minutes: int) -> list[HydrographPoint]:
    return [
        HydrographPoint(timestamp_minutes=0, flow_cms=flow_cms),
        HydrographPoint(timestamp_minutes=duration_minutes, flow_cms=flow_cms),
    ]


def release_only_repo() -> MemoryHydroRepository:
    return MemoryHydroRepository(
        objects=[reservoir(), reach("release-reach", k_minutes=30, x=0.2)],
        relations=[
            relation(
                "reservoir-discharge",
                "reservoir-alpha",
                "release-reach",
                RelationType.DISCHARGES_TO,
            )
        ],
    )


def test_release_request_requires_well_formed_inflow_and_release_boundaries():
    with pytest.raises(ValidationError):
        ReleaseScenarioRequest(
            reservoir_id="reservoir-alpha",
            duration_minutes=60,
            dt_minutes=30,
            max_hops=1,
            inflow_hydrograph=constant_boundary(100, 60),
        )

    with pytest.raises(ValidationError):
        ReleaseScenarioRequest(
            reservoir_id="reservoir-alpha",
            duration_minutes=50,
            dt_minutes=30,
            max_hops=1,
            inflow_hydrograph=constant_boundary(100, 60),
            release_hydrograph=constant_boundary(50, 60),
        )

    invalid_inflow = [
        HydrographPoint(timestamp_minutes=10, flow_cms=20),
        HydrographPoint(timestamp_minutes=60, flow_cms=40),
    ]
    with pytest.raises(ValidationError):
        ReleaseScenarioRequest(
            reservoir_id="reservoir-alpha",
            duration_minutes=60,
            dt_minutes=30,
            max_hops=1,
            inflow_hydrograph=invalid_inflow,
            release_hydrograph=constant_boundary(50, 60),
        )

    invalid_release = [
        HydrographPoint(timestamp_minutes=0, flow_cms=20),
        HydrographPoint(timestamp_minutes=30, flow_cms=40),
    ]
    with pytest.raises(ValidationError):
        ReleaseScenarioRequest(
            reservoir_id="reservoir-alpha",
            duration_minutes=60,
            dt_minutes=30,
            max_hops=1,
            inflow_hydrograph=constant_boundary(100, 60),
            release_hydrograph=invalid_release,
        )


def test_release_scenario_samples_release_and_integrates_both_hydrographs():
    result = run_release_scenario(
        release_only_repo(),
        ReleaseScenarioRequest(
            reservoir_id="reservoir-alpha",
            duration_minutes=60,
            dt_minutes=30,
            max_hops=1,
            inflow_hydrograph=constant_boundary(100, 60),
            release_hydrograph=[
                HydrographPoint(timestamp_minutes=0, flow_cms=20),
                HydrographPoint(timestamp_minutes=60, flow_cms=80),
            ],
        ),
    )

    release_states = [state for state in result.states if state.variable == "release"]
    assert [(state.timestamp_minutes, state.value) for state in release_states] == [
        (0, pytest.approx(20)),
        (30, pytest.approx(50)),
        (60, pytest.approx(80)),
    ]

    storage_states = [state for state in result.states if state.variable == "storage"]
    assert [state.value for state in storage_states] == [
        pytest.approx(1_000_000),
        pytest.approx(1_117_000),
        pytest.approx(1_180_000),
    ]


def test_release_scenario_routes_receiving_reach_before_downstream_reaches(monkeypatch):
    repo = MemoryHydroRepository(
        objects=[
            reservoir(),
            reach("receiving-reach", k_minutes=31, x=0.2),
            reach("downstream-reach", k_minutes=47, x=0.31),
        ],
        relations=[
            relation(
                "reservoir-discharge",
                "reservoir-alpha",
                "receiving-reach",
                RelationType.DISCHARGES_TO,
            ),
            relation(
                "network-flow",
                "receiving-reach",
                "downstream-reach",
                RelationType.FLOWS_TO,
            ),
        ],
    )
    captured = []

    def capture_route(inflow_cms, params, initial_outflow_cms=None):
        captured.append((list(inflow_cms), params, initial_outflow_cms))
        return list(inflow_cms)

    monkeypatch.setattr(scenario_module, "route_muskingum", capture_route)

    result = run_release_scenario(
        repo,
        ReleaseScenarioRequest(
            reservoir_id="reservoir-alpha",
            duration_minutes=60,
            dt_minutes=30,
            max_hops=1,
            inflow_hydrograph=constant_boundary(100, 60),
            release_hydrograph=[
                HydrographPoint(timestamp_minutes=0, flow_cms=10),
                HydrographPoint(timestamp_minutes=60, flow_cms=70),
            ],
        ),
    )

    flow_objects = {state.object_id for state in result.states if state.variable == "flow"}
    assert flow_objects == {"receiving-reach", "downstream-reach"}
    assert len(captured) == 2

    first_input, first_params, first_initial_outflow = captured[0]
    assert first_input == pytest.approx([10, 40, 70])
    assert first_initial_outflow == pytest.approx(10)
    assert first_params.k_seconds == pytest.approx(31 * 60)
    assert first_params.x == pytest.approx(0.2)

    second_input, second_params, second_initial_outflow = captured[1]
    assert second_input == pytest.approx([10, 40, 70])
    assert second_initial_outflow == pytest.approx(10)
    assert second_params.k_seconds == pytest.approx(47 * 60)
    assert second_params.x == pytest.approx(0.31)


@pytest.mark.parametrize(
    "relations",
    [
        [],
        [
            relation("discharge-a", "reservoir-alpha", "reach-a", RelationType.DISCHARGES_TO),
            relation("discharge-b", "reservoir-alpha", "reach-b", RelationType.DISCHARGES_TO),
        ],
    ],
)
def test_release_scenario_requires_exactly_one_discharge_target(relations):
    repo = MemoryHydroRepository(
        objects=[
            reservoir(),
            reach("reach-a", k_minutes=30, x=0.2),
            reach("reach-b", k_minutes=30, x=0.2),
        ],
        relations=relations,
    )

    with pytest.raises(ValueError, match="exactly one DISCHARGES_TO"):
        run_release_scenario(
            repo,
            ReleaseScenarioRequest(
                reservoir_id="reservoir-alpha",
                duration_minutes=30,
                dt_minutes=30,
                max_hops=1,
                inflow_hydrograph=constant_boundary(50, 30),
                release_hydrograph=constant_boundary(100, 30),
            ),
        )


def test_release_scenario_requires_stored_routing_parameters_on_receiving_reach():
    repo = MemoryHydroRepository(
        objects=[
            reservoir(),
            reach("receiving-reach", k_minutes=47),
            reach("downstream-reach", k_minutes=50, x=0.2),
        ],
        relations=[
            relation(
                "reservoir-discharge",
                "reservoir-alpha",
                "receiving-reach",
                RelationType.DISCHARGES_TO,
            ),
            relation("network-flow", "receiving-reach", "downstream-reach", RelationType.FLOWS_TO),
        ],
    )

    with pytest.raises(ValueError, match="routing_k_minutes and routing_x"):
        run_release_scenario(
            repo,
            ReleaseScenarioRequest(
                reservoir_id="reservoir-alpha",
                duration_minutes=30,
                dt_minutes=30,
                max_hops=1,
                inflow_hydrograph=constant_boundary(50, 30),
                release_hydrograph=constant_boundary(100, 30),
            ),
        )
