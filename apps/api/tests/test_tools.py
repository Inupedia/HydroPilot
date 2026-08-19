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
                properties={"initial_storage_m3": 1_000_000},
                source="test-repository",
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
                id="curve-area",
                object_id="reservoir-alpha",
                curve_type=CurveType.LEVEL_AREA,
                x_unit="m",
                y_unit="m2",
                points=[
                    HydroCurvePoint(x=100, y=50_000),
                    HydroCurvePoint(x=110, y=60_000),
                    HydroCurvePoint(x=120, y=70_000),
                ],
                source="test-area-source",
            ),
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
                source="test-storage-source",
            ),
        ]
        self.constraints = [
            HydroConstraint(
                id="constraint-level-range",
                object_id="reservoir-alpha",
                variable="level",
                constraint_type=ConstraintType.RANGE,
                unit="m",
                min_value=95,
                max_value=108,
                active_when={"season": "flood"},
                source="test-rulebook-range",
            ),
            HydroConstraint(
                id="constraint-max-release",
                object_id="reservoir-alpha",
                variable="release",
                constraint_type=ConstraintType.MAXIMUM,
                unit="m3/s",
                max_value=80,
                source="test-rulebook-release",
            ),
            HydroConstraint(
                id="constraint-min-level",
                object_id="reservoir-alpha",
                variable="level",
                constraint_type=ConstraintType.MINIMUM,
                unit="m",
                min_value=96,
                source="test-rulebook-min",
            ),
        ]

    def list_objects(self, object_type: ObjectType | None = None):
        values = list(self.objects.values())
        if object_type is not None:
            values = [item for item in values if item.object_type is object_type]
        return sorted(values, key=lambda item: item.id)

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
        return sorted(values, key=lambda item: item.id)

    def list_constraints(self, object_id=None, variable=None):
        values = self.constraints
        if object_id is not None:
            values = [item for item in values if item.object_id == object_id]
        if variable is not None:
            values = [item for item in values if item.variable == variable]
        return sorted(values, key=lambda item: item.id)


def test_catalog_contains_only_read_only_tools_with_json_schemas():
    catalog = tool_catalog()

    assert [item.name for item in catalog] == [
        "get_object",
        "list_constraints",
        "list_curves",
        "list_objects",
        "trace_downstream",
    ]
    assert all(item.read_only is True for item in catalog)
    assert all(item.input_schema["type"] == "object" for item in catalog)
    assert all("properties" in item.input_schema for item in catalog)


def test_get_object_tool_still_returns_full_domain_data():
    result = execute_tool(
        ToolRepository(),
        HydroToolRequest(name="get_object", arguments={"object_id": "reservoir-alpha"}),
    )

    assert result.name == "get_object"
    assert result.result["id"] == "reservoir-alpha"
    assert result.result["object_type"] == "reservoir"
    assert result.result["geometry"] == {"type": "Point", "coordinates": [0.0, 0.0]}
    assert result.result["properties"] == {"initial_storage_m3": 1_000_000}
    assert result.result["source"] == "test-repository"


def test_list_objects_tool_returns_compact_paged_inventory_with_typed_filter():
    repo = ToolRepository()

    all_objects = execute_tool(repo, HydroToolRequest(name="list_objects", arguments={}))
    reaches = execute_tool(
        repo,
        HydroToolRequest(name="list_objects", arguments={"object_type": "river_reach"}),
    )

    assert all_objects.result["offset"] == 0
    assert all_objects.result["limit"] == 50
    assert all_objects.result["total"] == 3
    assert [item["id"] for item in all_objects.result["items"]] == ["reach-a", "reach-b", "reservoir-alpha"]
    assert all(set(item) == {"id", "name", "object_type", "source"} for item in all_objects.result["items"])
    assert all("geometry" not in item and "properties" not in item for item in all_objects.result["items"])

    assert reaches.result["total"] == 2
    assert [item["id"] for item in reaches.result["items"]] == ["reach-a", "reach-b"]
    assert all(item["object_type"] == "river_reach" for item in reaches.result["items"])


def test_list_objects_tool_paginates_deterministically_and_bounds_limit():
    repo = ToolRepository()

    page = execute_tool(
        repo,
        HydroToolRequest(name="list_objects", arguments={"offset": 1, "limit": 1}),
    )
    beyond = execute_tool(
        repo,
        HydroToolRequest(name="list_objects", arguments={"offset": 10, "limit": 2}),
    )

    assert page.result == {
        "offset": 1,
        "limit": 1,
        "total": 3,
        "items": [
            {
                "id": "reach-b",
                "name": "Reach B",
                "object_type": "river_reach",
                "source": "fixture",
            }
        ],
    }
    assert beyond.result == {"offset": 10, "limit": 2, "total": 3, "items": []}

    with pytest.raises(ValidationError):
        execute_tool(
            repo,
            HydroToolRequest(name="list_objects", arguments={"limit": 101}),
        )

    with pytest.raises(ValidationError):
        execute_tool(
            repo,
            HydroToolRequest(name="list_objects", arguments={"object_type": "not-a-real-object-type"}),
        )


def test_trace_downstream_tool_respects_hop_limit():
    result = execute_tool(
        ToolRepository(),
        HydroToolRequest(name="trace_downstream", arguments={"object_id": "reach-a", "max_hops": 1}),
    )

    assert result.result == [{"object_id": "reach-b", "hop": 1, "via_relation": "FLOWS_TO"}]


def test_list_curves_tool_returns_compact_paged_catalog_with_typed_filter():
    repo = ToolRepository()

    all_curves = execute_tool(
        repo,
        HydroToolRequest(name="list_curves", arguments={"object_id": "reservoir-alpha"}),
    )
    storage = execute_tool(
        repo,
        HydroToolRequest(
            name="list_curves",
            arguments={"object_id": "reservoir-alpha", "curve_type": "level_storage"},
        ),
    )

    assert all_curves.result["offset"] == 0
    assert all_curves.result["limit"] == 20
    assert all_curves.result["total"] == 2
    assert all_curves.result["items"] == [
        {
            "id": "curve-area",
            "object_id": "reservoir-alpha",
            "curve_type": "level_area",
            "x_unit": "m",
            "y_unit": "m2",
            "point_count": 3,
            "source": "test-area-source",
        },
        {
            "id": "curve-storage",
            "object_id": "reservoir-alpha",
            "curve_type": "level_storage",
            "x_unit": "m",
            "y_unit": "m3",
            "point_count": 2,
            "source": "test-storage-source",
        },
    ]
    assert all("points" not in item for item in all_curves.result["items"])
    assert storage.result["total"] == 1
    assert [item["id"] for item in storage.result["items"]] == ["curve-storage"]


def test_list_curves_tool_paginates_and_bounds_limit():
    repo = ToolRepository()

    page = execute_tool(
        repo,
        HydroToolRequest(
            name="list_curves",
            arguments={"object_id": "reservoir-alpha", "offset": 1, "limit": 1},
        ),
    )
    beyond = execute_tool(
        repo,
        HydroToolRequest(
            name="list_curves",
            arguments={"object_id": "reservoir-alpha", "offset": 10, "limit": 2},
        ),
    )

    assert page.result["offset"] == 1
    assert page.result["limit"] == 1
    assert page.result["total"] == 2
    assert [item["id"] for item in page.result["items"]] == ["curve-storage"]
    assert beyond.result == {"offset": 10, "limit": 2, "total": 2, "items": []}

    with pytest.raises(ValidationError):
        execute_tool(
            repo,
            HydroToolRequest(
                name="list_curves",
                arguments={"object_id": "reservoir-alpha", "limit": 51},
            ),
        )


def test_list_constraints_tool_returns_paged_full_semantics_with_variable_filter():
    repo = ToolRepository()

    all_constraints = execute_tool(
        repo,
        HydroToolRequest(name="list_constraints", arguments={"object_id": "reservoir-alpha"}),
    )
    levels = execute_tool(
        repo,
        HydroToolRequest(
            name="list_constraints",
            arguments={"object_id": "reservoir-alpha", "variable": "level"},
        ),
    )

    assert all_constraints.result["offset"] == 0
    assert all_constraints.result["limit"] == 50
    assert all_constraints.result["total"] == 3
    assert [item["id"] for item in all_constraints.result["items"]] == [
        "constraint-level-range",
        "constraint-max-release",
        "constraint-min-level",
    ]

    range_constraint = all_constraints.result["items"][0]
    assert range_constraint == {
        "id": "constraint-level-range",
        "object_id": "reservoir-alpha",
        "variable": "level",
        "constraint_type": "range",
        "unit": "m",
        "min_value": 95.0,
        "max_value": 108.0,
        "active_when": {"season": "flood"},
        "source": "test-rulebook-range",
    }

    assert levels.result["total"] == 2
    assert [item["id"] for item in levels.result["items"]] == [
        "constraint-level-range",
        "constraint-min-level",
    ]


def test_list_constraints_tool_paginates_and_bounds_limit():
    repo = ToolRepository()

    page = execute_tool(
        repo,
        HydroToolRequest(
            name="list_constraints",
            arguments={"object_id": "reservoir-alpha", "offset": 1, "limit": 1},
        ),
    )
    beyond = execute_tool(
        repo,
        HydroToolRequest(
            name="list_constraints",
            arguments={"object_id": "reservoir-alpha", "offset": 10, "limit": 2},
        ),
    )

    assert page.result["offset"] == 1
    assert page.result["limit"] == 1
    assert page.result["total"] == 3
    assert [item["id"] for item in page.result["items"]] == ["constraint-max-release"]
    assert beyond.result == {"offset": 10, "limit": 2, "total": 3, "items": []}

    with pytest.raises(ValidationError):
        execute_tool(
            repo,
            HydroToolRequest(
                name="list_constraints",
                arguments={"object_id": "reservoir-alpha", "limit": 101},
            ),
        )


def test_unknown_tool_and_invalid_arguments_fail_explicitly():
    with pytest.raises(ValueError, match="unknown hydro tool"):
        execute_tool(ToolRepository(), HydroToolRequest(name="delete_everything", arguments={}))

    with pytest.raises(ValidationError):
        execute_tool(ToolRepository(), HydroToolRequest(name="get_object", arguments={}))


def test_object_specific_read_tools_raise_key_error_for_missing_object():
    repo = ToolRepository()

    for name, arguments in [
        ("get_object", {"object_id": "missing"}),
        ("trace_downstream", {"object_id": "missing"}),
        ("list_curves", {"object_id": "missing"}),
        ("list_constraints", {"object_id": "missing"}),
    ]:
        with pytest.raises(KeyError, match="missing"):
            execute_tool(repo, HydroToolRequest(name=name, arguments=arguments))
