import math

import pytest

from hydropilot_api.domain import Geometry, HydroObject, HydroRelation, ObjectType, RelationType
from hydropilot_api.services.scenario import HydrographPoint, ReleaseScenarioRequest, run_release_scenario


class ReservoirConfigRepository:
    def __init__(self, reservoir_properties: dict):
        self.objects = {
            "reservoir-alpha": HydroObject(
                id="reservoir-alpha",
                name="Reservoir Alpha",
                object_type=ObjectType.RESERVOIR,
                geometry=Geometry(type="Point", coordinates=[-122.0, 40.0]),
                properties=reservoir_properties,
            ),
            "receiving-reach": HydroObject(
                id="receiving-reach",
                name="Receiving Reach",
                object_type=ObjectType.RIVER_REACH,
                geometry=Geometry(type="LineString", coordinates=[[-122.0, 40.0], [-121.9, 39.9]]),
                properties={"routing_k_minutes": 30, "routing_x": 0.2},
            ),
        }
        self.relations = [
            HydroRelation(
                id="reservoir-discharge",
                source_id="reservoir-alpha",
                target_id="receiving-reach",
                relation_type=RelationType.DISCHARGES_TO,
            )
        ]

    def list_objects(self, object_type=None):
        values = list(self.objects.values())
        if object_type is not None:
            values = [item for item in values if item.object_type is object_type]
        return values

    def get_object(self, object_id):
        return self.objects.get(object_id)

    def list_relations(self):
        return self.relations

    def list_curves(self, object_id=None, curve_type=None):
        return []

    def list_constraints(self, object_id=None, variable=None):
        return []


def request() -> ReleaseScenarioRequest:
    return ReleaseScenarioRequest(
        reservoir_id="reservoir-alpha",
        duration_minutes=30,
        dt_minutes=30,
        max_hops=1,
        inflow_hydrograph=[
            HydrographPoint(timestamp_minutes=0, flow_cms=100),
            HydrographPoint(timestamp_minutes=30, flow_cms=100),
        ],
        release_hydrograph=[
            HydrographPoint(timestamp_minutes=0, flow_cms=50),
            HydrographPoint(timestamp_minutes=30, flow_cms=50),
        ],
    )


@pytest.mark.parametrize(
    "properties",
    [
        {"max_storage_m3": 2_000_000},
        {"initial_storage_m3": 1_000_000},
        {"initial_storage_m3": None, "max_storage_m3": 2_000_000},
        {"initial_storage_m3": 1_000_000, "max_storage_m3": None},
    ],
)
def test_release_scenario_requires_explicit_reservoir_storage_inputs(properties):
    with pytest.raises(
        ValueError,
        match="reservoir reservoir-alpha requires initial_storage_m3 and max_storage_m3",
    ):
        run_release_scenario(ReservoirConfigRepository(properties), request())


@pytest.mark.parametrize(
    "properties",
    [
        {"initial_storage_m3": "not-a-number", "max_storage_m3": 2_000_000},
        {"initial_storage_m3": 1_000_000, "max_storage_m3": "not-a-number"},
        {"initial_storage_m3": math.nan, "max_storage_m3": 2_000_000},
        {"initial_storage_m3": 1_000_000, "max_storage_m3": math.inf},
    ],
)
def test_release_scenario_rejects_invalid_or_non_finite_storage_inputs(properties):
    with pytest.raises(
        ValueError,
        match="reservoir reservoir-alpha has invalid initial_storage_m3 or max_storage_m3",
    ):
        run_release_scenario(ReservoirConfigRepository(properties), request())


def test_release_scenario_uses_explicit_valid_storage_inputs_without_fallbacks():
    result = run_release_scenario(
        ReservoirConfigRepository(
            {
                "initial_storage_m3": 1_000_000,
                "max_storage_m3": 2_000_000,
            }
        ),
        request(),
    )

    storage = [state for state in result.states if state.variable == "storage"]
    assert [state.value for state in storage] == [
        pytest.approx(1_000_000),
        pytest.approx(1_090_000),
    ]
