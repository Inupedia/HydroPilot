import pytest
from pydantic import ValidationError

from hydropilot_api.domain import (
    ConstraintType,
    CurveType,
    Geometry,
    HydroConstraint,
    HydroCurve,
    HydroCurvePoint,
    HydroObject,
    HydroRelation,
    HydroRule,
    ObjectType,
    RelationType,
)


def test_dispatch_asset_vocabulary_is_typed_and_additive():
    expected = {
        "channel",
        "tunnel",
        "aqueduct",
        "siphon",
        "pump_station",
        "gate",
        "diversion",
        "intake",
        "powerhouse",
        "spillway",
        "outlet",
        "flood_storage",
        "levee",
        "water_use_unit",
        "irrigation_district",
        "control_section",
    }
    assert expected.issubset({item.value for item in ObjectType})

    gate = HydroObject(
        id="gate-001",
        name="Gate 1",
        object_type=ObjectType.GATE,
        geometry=Geometry(type="Point", coordinates=[-121.5, 38.5]),
    )
    assert gate.object_type is ObjectType.GATE


def test_operational_relationship_vocabulary_supports_dispatch_graphs():
    expected = {"CONVEYS_TO", "DIVERTS_TO", "REGULATES", "SERVES", "BELONGS_TO"}
    assert expected.issubset({item.value for item in RelationType})

    relation = HydroRelation(
        id="relation-001",
        source_id="gate-001",
        target_id="channel-001",
        relation_type=RelationType.REGULATES,
    )
    assert relation.relation_type is RelationType.REGULATES


def test_engineering_curve_accepts_strictly_increasing_points():
    curve = HydroCurve(
        id="curve-shasta-storage",
        object_id="reservoir-shasta",
        curve_type=CurveType.LEVEL_STORAGE,
        x_unit="m",
        y_unit="m3",
        points=[
            HydroCurvePoint(x=250.0, y=1_000_000.0),
            HydroCurvePoint(x=260.0, y=1_400_000.0),
            HydroCurvePoint(x=270.0, y=1_900_000.0),
        ],
    )
    assert curve.points[-1].y == 1_900_000.0


@pytest.mark.parametrize(
    "points",
    [
        [HydroCurvePoint(x=250.0, y=1_000_000.0)],
        [
            HydroCurvePoint(x=250.0, y=1_000_000.0),
            HydroCurvePoint(x=250.0, y=1_400_000.0),
        ],
        [
            HydroCurvePoint(x=260.0, y=1_400_000.0),
            HydroCurvePoint(x=250.0, y=1_000_000.0),
        ],
    ],
)
def test_engineering_curve_rejects_unusable_point_sequences(points):
    with pytest.raises(ValidationError):
        HydroCurve(
            id="curve-invalid",
            object_id="reservoir-shasta",
            curve_type=CurveType.LEVEL_STORAGE,
            x_unit="m",
            y_unit="m3",
            points=points,
        )


def test_constraint_types_require_their_relevant_bounds():
    minimum = HydroConstraint(
        id="constraint-min-flow",
        object_id="outlet-001",
        variable="flow",
        constraint_type=ConstraintType.MINIMUM,
        min_value=12.0,
        unit="m3/s",
    )
    maximum = HydroConstraint(
        id="constraint-max-level",
        object_id="reservoir-shasta",
        variable="level",
        constraint_type=ConstraintType.MAXIMUM,
        max_value=325.0,
        unit="m",
    )
    interval = HydroConstraint(
        id="constraint-level-range",
        object_id="reservoir-shasta",
        variable="level",
        constraint_type=ConstraintType.RANGE,
        min_value=250.0,
        max_value=325.0,
        unit="m",
    )
    ramp = HydroConstraint(
        id="constraint-ramp",
        object_id="outlet-001",
        variable="flow",
        constraint_type=ConstraintType.RAMP_RATE,
        max_value=100.0,
        unit="m3/s/h",
    )

    assert minimum.min_value == 12.0
    assert maximum.max_value == 325.0
    assert interval.min_value < interval.max_value
    assert ramp.max_value == 100.0


@pytest.mark.parametrize(
    "payload",
    [
        {"constraint_type": ConstraintType.MINIMUM, "min_value": None, "max_value": 10.0},
        {"constraint_type": ConstraintType.MAXIMUM, "min_value": 1.0, "max_value": None},
        {"constraint_type": ConstraintType.RANGE, "min_value": None, "max_value": 10.0},
        {"constraint_type": ConstraintType.RANGE, "min_value": 20.0, "max_value": 10.0},
        {"constraint_type": ConstraintType.RAMP_RATE, "min_value": None, "max_value": None},
    ],
)
def test_constraint_rejects_invalid_bound_shapes(payload):
    with pytest.raises(ValidationError):
        HydroConstraint(
            id="constraint-invalid",
            object_id="reservoir-shasta",
            variable="level",
            unit="m",
            **payload,
        )


def test_operating_rule_preserves_machine_readable_condition_and_action():
    rule = HydroRule(
        id="rule-flood-limit",
        name="Flood-limit release rule",
        object_id="reservoir-shasta",
        priority=100,
        condition={"all": [{"variable": "level", "op": ">", "value": 320.0}]},
        action={"type": "set_release", "value": 1200.0, "unit": "m3/s"},
        source="demo-rulebook",
    )

    assert rule.priority == 100
    assert rule.condition["all"][0]["variable"] == "level"
    assert rule.action["type"] == "set_release"
