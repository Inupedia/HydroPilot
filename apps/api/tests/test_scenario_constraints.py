import pytest

from hydropilot_api.domain import (
    ConstraintType,
    Geometry,
    HydroConstraint,
    HydroObject,
    HydroRelation,
    ObjectType,
    RelationType,
)
from hydropilot_api.services import scenario as scenario_module
from hydropilot_api.services.scenario import HydrographPoint, ReleaseScenarioRequest, run_release_scenario


class ConstraintScenarioRepository:
    def __init__(self, constraints: list[HydroConstraint]):
        self.objects = {
            "reservoir-alpha": HydroObject(
                id="reservoir-alpha",
                name="Reservoir Alpha",
                object_type=ObjectType.RESERVOIR,
                geometry=Geometry(type="Point", coordinates=[-122.0, 40.0]),
                properties={"initial_storage_m3": 1_000_000, "max_storage_m3": 2_000_000},
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
        self.constraints = constraints

    def list_objects(self, object_type: ObjectType | None = None):
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
        values = self.constraints
        if object_id is not None:
            values = [item for item in values if item.object_id == object_id]
        if variable is not None:
            values = [item for item in values if item.variable == variable]
        return sorted(values, key=lambda item: item.id)


def request(*, start_release: float = 20, end_release: float = 80) -> ReleaseScenarioRequest:
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
            HydrographPoint(timestamp_minutes=0, flow_cms=start_release),
            HydrographPoint(timestamp_minutes=60, flow_cms=end_release),
        ],
    )


def constraint(
    constraint_id: str,
    *,
    object_id: str = "reservoir-alpha",
    variable: str = "release",
    constraint_type: ConstraintType,
    unit: str = "m3/s",
    min_value: float | None = None,
    max_value: float | None = None,
    active_when: dict | None = None,
) -> HydroConstraint:
    return HydroConstraint(
        id=constraint_id,
        object_id=object_id,
        variable=variable,
        constraint_type=constraint_type,
        unit=unit,
        min_value=min_value,
        max_value=max_value,
        active_when=active_when or {},
        source="test-rulebook",
    )


def test_unconditional_min_max_range_report_only_real_violations():
    repo = ConstraintScenarioRepository(
        [
            constraint("max-release", constraint_type=ConstraintType.MAXIMUM, max_value=50),
            constraint("min-release", constraint_type=ConstraintType.MINIMUM, min_value=20),
            constraint("range-release", constraint_type=ConstraintType.RANGE, min_value=20, max_value=70),
        ]
    )

    result = run_release_scenario(repo, request())

    assert [
        (item.constraint_id, item.timestamp_minutes, item.value)
        for item in result.violations
    ] == [
        ("max-release", 60, pytest.approx(80)),
        ("range-release", 60, pytest.approx(80)),
    ]
    assert result.unevaluated_constraints == []


def test_supported_hourly_ramp_rate_reports_adjacent_rate_violations_without_mutating_states():
    repo = ConstraintScenarioRepository(
        [
            constraint(
                "ramp-release",
                constraint_type=ConstraintType.RAMP_RATE,
                max_value=59,
                unit="m3/s/h",
            )
        ]
    )

    result = run_release_scenario(repo, request())

    assert [
        (item.timestamp_minutes, item.value, item.unit)
        for item in result.violations
    ] == [
        (30, pytest.approx(60), "m3/s/h"),
        (60, pytest.approx(60), "m3/s/h"),
    ]
    assert result.unevaluated_constraints == []
    assert [state.value for state in result.states if state.object_id == "reservoir-alpha" and state.variable == "release"] == pytest.approx([20, 50, 80])


def test_hourly_ramp_rate_allows_equality_at_limit():
    repo = ConstraintScenarioRepository(
        [
            constraint(
                "ramp-release",
                constraint_type=ConstraintType.RAMP_RATE,
                max_value=60,
                unit="m3/s/h",
            )
        ]
    )

    result = run_release_scenario(repo, request())

    assert result.violations == []
    assert result.unevaluated_constraints == []


def test_hourly_ramp_rate_uses_absolute_change_for_decreasing_values():
    repo = ConstraintScenarioRepository(
        [
            constraint(
                "ramp-release",
                constraint_type=ConstraintType.RAMP_RATE,
                max_value=59,
                unit="m3/s/h",
            )
        ]
    )

    result = run_release_scenario(repo, request(start_release=80, end_release=20))

    assert [(item.timestamp_minutes, item.value) for item in result.violations] == [
        (30, pytest.approx(60)),
        (60, pytest.approx(60)),
    ]


def test_conditional_unsupported_ramp_and_missing_variable_are_explicitly_unevaluated():
    repo = ConstraintScenarioRepository(
        [
            constraint(
                "conditional-release",
                constraint_type=ConstraintType.RAMP_RATE,
                max_value=10,
                unit="m3/s/h",
                active_when={"season": "flood"},
            ),
            constraint(
                "ramp-release",
                constraint_type=ConstraintType.RAMP_RATE,
                max_value=10,
                unit="m3/s/min",
            ),
            constraint(
                "missing-variable",
                variable="evaporation",
                constraint_type=ConstraintType.MINIMUM,
                min_value=0,
            ),
        ]
    )

    result = run_release_scenario(repo, request())

    assert result.violations == []
    assert [(item.constraint_id, item.reason) for item in result.unevaluated_constraints] == [
        ("conditional-release", "conditional constraints are not evaluated"),
        ("missing-variable", "scenario has no matching state variable"),
        ("ramp-release", "ramp-rate unit m3/s/min is unsupported; expected m3/s/h"),
    ]


def test_supported_constraint_rejects_unit_mismatch():
    repo = ConstraintScenarioRepository(
        [
            constraint(
                "wrong-unit-release",
                constraint_type=ConstraintType.MAXIMUM,
                max_value=100,
                unit="cfs",
            )
        ]
    )

    with pytest.raises(ValueError, match="constraint unit cfs does not match scenario unit m3/s"):
        run_release_scenario(repo, request())


def test_constraint_evaluation_covers_routed_reach_flow(monkeypatch):
    repo = ConstraintScenarioRepository(
        [
            constraint(
                "max-reach-flow",
                object_id="receiving-reach",
                variable="flow",
                constraint_type=ConstraintType.MAXIMUM,
                max_value=40,
            )
        ]
    )

    def identity_route(inflow_cms, params, initial_outflow_cms=None):
        return list(inflow_cms)

    monkeypatch.setattr(scenario_module, "route_muskingum", identity_route)

    result = run_release_scenario(repo, request())

    assert [(item.timestamp_minutes, item.value) for item in result.violations] == [
        (30, pytest.approx(50)),
        (60, pytest.approx(80)),
    ]
    assert all(item.object_id == "receiving-reach" for item in result.violations)
