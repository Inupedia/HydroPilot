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
    ObjectType,
    RelationType,
)
from hydropilot_api.tools import HydroToolRequest, execute_tool, tool_catalog


class ToolRepository:
    def __init__(self):
        self.objects = {
            "reach-a": HydroObject(
                id="reach-a",
                name="Reach A",
                object_type=ObjectType.RIVER_REACH,
                geometry=Geometry(type="LineString", coordinates=[[0.0, 0.0], [1.0, 1.0]]),
            ),
            "reach-b": HydroObject(
                id="reach-b",
                name="Reach B",
                object_type=ObjectType.RIVER_REACH,
                geometry=Geometry(type="LineString", coordinates=[[1.0, 1.0], [2.0, 2.0]]),
            ),
            "reservoir-alpha": HydroObject(
                id="reservoir-alpha",
                name="Reservoir Alpha",
                object_type=ObjectType.RESERVOIR,
                geometry=Geometry(type="Point", coordinates=[0.0, 0.0]),
            ),
        }
        self.relations = [
            HydroRelation(
                id="flow-a-b",
                source_id="reach-a",
                target_id="reach-b",
                relation_type=RelationType.FLOWS_TO,
            )
        ]
        self.curves = [
            HydroCurve(
                id="curve-storage",
                object_id="reservoir-alpha",
                curve_type=CurveType.LEVEL_STORAGE,
                x_unit="m",
                y_unit="m3",
                points=[
                    HydroCurvePoint(x=100, y=1_000_000),
                    HydroCurvePoint(x=110, y=1_200_000),
                ],
                source="test",
            )
        ]
        self.constraints = [
            HydroConstraint(
                id="constraint-level",
                object_id="reservoir-alpha",
                variable="level",
                constraint_type=ConstraintType.MAXIMUM,
                unit="m",
                max_value=108,
                source="test",
            )
        ]

    def get_object(self, object_id):
        return self.objects.get(object_id)

    def list_relations(self):
        return self.relations

    def list_curves(self, object_id=None, curve_type=None):
        values = self.curves
        if object_id is not None:
            values = [item for item in values if item.object_id == object_id]
        if curve_type is not None:
            values = [item for item in values if item.curve_type is curve_type]
        return values

    def list_constraints(self, object_id=None, variable=None):
        values = self.constraints
        if object_id is not None:
            values = [item for item in values if item.object_id == object_id]
        if variable is not None:
            values = [item for item in values if item.variable == variable]
        return values


def test_catalog_contains_only_initial_read_only_tools_with_json_schemas():
    catalog = tool_catalog()

    assert [item.name for item in catalog] == [
        "get_object",
        "list_constraints",
        "list_curves",
        "trace_downstream",
    ]
    assert all(item.read_only is True for item in catalog)
    assert all(item.input_schema["type"] == "object" for item in catalog)
    assert all("properties" in item.input_schema for item in catalog)


def test_get_object_tool_returns_json_serializable_domain_data():
    result = execute_tool(
        ToolRepository(),
        HydroToolRequest(name="get_object", arguments={"object_id": "reservoir-alpha"}),
    )

    assert result.name == "get_object"
    assert result.result["id"] == "reservoir-alpha"
    assert result.result["object_type"] == "reservoir"


def test_trace_downstream_tool_respects_hop_limit():
    result = execute_tool(
        ToolRepository(),
        HydroToolRequest(name="trace_downstream", arguments={"object_id": "reach-a", "max_hops": 1}),
    )

    assert result.result == [{"object_id": "reach-b", "hop": 1, "via_relation": "FLOWS_TO"}]


def test_curve_and_constraint_tools_preserve_typed_filters():
    repo = ToolRepository()

    curves = execute_tool(
        repo,
        HydroToolRequest(
            name="list_curves",
            arguments={"object_id": "reservoir-alpha", "curve_type": "level_storage"},
        ),
    )
    constraints = execute_tool(
        repo,
        HydroToolRequest(
            name="list_constraints",
            arguments={"object_id": "reservoir-alpha", "variable": "level"},
        ),
    )

    assert [item["id"] for item in curves.result] == ["curve-storage"]
    assert curves.result[0]["curve_type"] == "level_storage"
    assert [item["id"] for item in constraints.result] == ["constraint-level"]
    assert constraints.result[0]["constraint_type"] == "maximum"


def test_unknown_tool_and_invalid_arguments_fail_explicitly():
    with pytest.raises(ValueError, match="unknown hydro tool"):
        execute_tool(ToolRepository(), HydroToolRequest(name="delete_everything", arguments={}))

    with pytest.raises(ValidationError):
        execute_tool(ToolRepository(), HydroToolRequest(name="get_object", arguments={}))


def test_read_tools_raise_key_error_for_missing_object():
    repo = ToolRepository()

    for name, arguments in [
        ("get_object", {"object_id": "missing"}),
        ("trace_downstream", {"object_id": "missing"}),
        ("list_curves", {"object_id": "missing"}),
        ("list_constraints", {"object_id": "missing"}),
    ]:
        with pytest.raises(KeyError, match="missing"):
            execute_tool(repo, HydroToolRequest(name=name, arguments=arguments))
