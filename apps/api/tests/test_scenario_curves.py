import pytest

from hydropilot_api.domain import (
    CurveType,
    Geometry,
    HydroCurve,
    HydroCurvePoint,
    HydroObject,
    HydroRelation,
    ObjectType,
    RelationType,
)
from hydropilot_api.services.scenario import HydrographPoint, ReleaseScenarioRequest, run_release_scenario


class MemoryHydroRepository:
    def __init__(
        self,
        objects: list[HydroObject],
        relations: list[HydroRelation],
        curves: list[HydroCurve] | None = None,
    ):
        self._objects = {item.id: item for item in objects}
        self._relations = relations
        self._curves = curves or []

    def list_objects(self, object_type: ObjectType | None = None) -> list[HydroObject]:
        values = list(self._objects.values())
        if object_type is not None:
            values = [item for item in values if item.object_type is object_type]
        return values

    def get_object(self, object_id: str) -> HydroObject | None:
        return self._objects.get(object_id)

    def list_relations(self) -> list[HydroRelation]:
        return self._relations

    def list_curves(
        self,
        object_id: str | None = None,
        curve_type: CurveType | None = None,
    ) -> list[HydroCurve]:
        values = self._curves
        if object_id is not None:
            values = [curve for curve in values if curve.object_id == object_id]
        if curve_type is not None:
            values = [curve for curve in values if curve.curve_type is curve_type]
        return sorted(values, key=lambda curve: curve.id)

    def list_constraints(self, object_id=None, variable=None):
        return []


def reservoir() -> HydroObject:
    return HydroObject(
        id="reservoir-alpha",
        name="Reservoir Alpha",
        object_type=ObjectType.RESERVOIR,
        geometry=Geometry(type="Point", coordinates=[-122.0, 40.0]),
        properties={
            "initial_storage_m3": 1_000_000,
            "max_storage_m3": 2_000_000,
            "initial_level_m": 999.0,
        },
    )


def receiving_reach() -> HydroObject:
    return HydroObject(
        id="receiving-reach",
        name="Receiving Reach",
        object_type=ObjectType.RIVER_REACH,
        geometry=Geometry(type="LineString", coordinates=[[-122.0, 40.0], [-121.9, 39.9]]),
        properties={"routing_k_minutes": 30, "routing_x": 0.2},
    )


def discharge_relation() -> HydroRelation:
    return HydroRelation(
        id="reservoir-discharge",
        source_id="reservoir-alpha",
        target_id="receiving-reach",
        relation_type=RelationType.DISCHARGES_TO,
    )


def level_storage_curve(
    curve_id: str = "curve-level-storage",
    *,
    x_unit: str = "m",
    y_unit: str = "m3",
    points: list[HydroCurvePoint] | None = None,
) -> HydroCurve:
    return HydroCurve(
        id=curve_id,
        object_id="reservoir-alpha",
        curve_type=CurveType.LEVEL_STORAGE,
        x_unit=x_unit,
        y_unit=y_unit,
        points=points
        or [
            HydroCurvePoint(x=100.0, y=900_000.0),
            HydroCurvePoint(x=110.0, y=1_100_000.0),
            HydroCurvePoint(x=120.0, y=1_300_000.0),
        ],
        source="test-engineering-data",
    )


def request() -> ReleaseScenarioRequest:
    return ReleaseScenarioRequest(
        reservoir_id="reservoir-alpha",
        duration_minutes=60,
        dt_minutes=30,
        max_hops=1,
        inflow_hydrograph=[
            HydrographPoint(timestamp_minutes=0, flow_cms=100),
            HydrographPoint(timestamp_minutes=60, flow_cms=100),
        ],
        release_hydrograph=[
            HydrographPoint(timestamp_minutes=0, flow_cms=50),
            HydrographPoint(timestamp_minutes=60, flow_cms=50),
        ],
    )


def repo_with_curves(curves: list[HydroCurve]) -> MemoryHydroRepository:
    return MemoryHydroRepository(
        objects=[reservoir(), receiving_reach()],
        relations=[discharge_relation()],
        curves=curves,
    )


def test_release_scenario_uses_repository_level_storage_curve_for_all_level_states():
    result = run_release_scenario(repo_with_curves([level_storage_curve()]), request())

    level_states = [state for state in result.states if state.variable == "level"]
    assert [(state.timestamp_minutes, state.value) for state in level_states] == [
        (0, pytest.approx(105.0)),
        (30, pytest.approx(109.5)),
        (60, pytest.approx(114.0)),
    ]


def test_release_scenario_rejects_wrong_level_storage_units():
    with pytest.raises(ValueError, match="level-storage curve requires x_unit=m and y_unit=m3"):
        run_release_scenario(repo_with_curves([level_storage_curve(x_unit="ft")]), request())


def test_release_scenario_rejects_ambiguous_level_storage_curves():
    with pytest.raises(ValueError, match="at most one level-storage curve"):
        run_release_scenario(
            repo_with_curves(
                [
                    level_storage_curve("curve-a"),
                    level_storage_curve("curve-b"),
                ]
            ),
            request(),
        )


def test_release_scenario_rejects_storage_outside_curve_domain():
    curve = level_storage_curve(
        points=[
            HydroCurvePoint(x=110.0, y=1_100_000.0),
            HydroCurvePoint(x=120.0, y=1_300_000.0),
        ]
    )

    with pytest.raises(ValueError, match="storage outside storage-level curve domain"):
        run_release_scenario(repo_with_curves([curve]), request())
