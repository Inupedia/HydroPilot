import pytest
from pydantic import ValidationError

from hydropilot_api.domain import Geometry, HydroObject, ObjectType
from hydropilot_api.tools import HydroToolRequest, execute_tool, tool_catalog


class StrictToolRepository:
    def __init__(self):
        self.object = HydroObject(
            id="reach-a",
            name="Reach A",
            object_type=ObjectType.RIVER_REACH,
            geometry=Geometry(type="LineString", coordinates=[[0.0, 0.0], [1.0, 1.0]]),
        )

    def list_objects(self, object_type=None):
        if object_type is not None and object_type is not ObjectType.RIVER_REACH:
            return []
        return [self.object]

    def get_object(self, object_id):
        return self.object if object_id == self.object.id else None

    def list_relations(self):
        return []

    def list_curves(self, object_id=None, curve_type=None):
        return []

    def list_constraints(self, object_id=None, variable=None):
        return []


def test_every_hydro_tool_schema_forbids_additional_properties():
    for definition in tool_catalog():
        assert definition.input_schema["additionalProperties"] is False


def test_known_tool_rejects_unknown_argument_before_execution():
    with pytest.raises(ValidationError) as exc_info:
        execute_tool(
            StrictToolRepository(),
            HydroToolRequest(
                name="get_object",
                arguments={"object_id": "reach-a", "delete": True},
            ),
        )

    assert any(error["type"] == "extra_forbidden" for error in exc_info.value.errors())


def test_hydro_tool_request_rejects_unknown_top_level_field():
    with pytest.raises(ValidationError) as exc_info:
        HydroToolRequest.model_validate(
            {
                "name": "get_object",
                "arguments": {"object_id": "reach-a"},
                "trusted": True,
            }
        )

    assert any(error["type"] == "extra_forbidden" for error in exc_info.value.errors())


def test_tool_response_reports_normalized_effective_arguments_with_defaults():
    response = execute_tool(
        StrictToolRepository(),
        HydroToolRequest(
            name="trace_downstream",
            arguments={"object_id": "reach-a"},
        ),
    )

    assert response.arguments == {
        "object_id": "reach-a",
        "max_hops": 8,
        "offset": 0,
        "limit": 100,
    }
    assert response.result == {
        "offset": 0,
        "limit": 100,
        "has_more": False,
        "items": [],
    }


def test_tool_response_normalizes_declared_enum_and_paging_fields():
    response = execute_tool(
        StrictToolRepository(),
        HydroToolRequest(
            name="list_objects",
            arguments={"object_type": "river_reach", "limit": "10"},
        ),
    )

    assert response.arguments == {
        "object_type": "river_reach",
        "offset": 0,
        "limit": 10,
    }
