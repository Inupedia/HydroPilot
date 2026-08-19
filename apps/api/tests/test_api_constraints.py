from fastapi.testclient import TestClient

import hydropilot_api.main as main_module
from hydropilot_api.domain import (
    ConstraintType,
    Geometry,
    HydroConstraint,
    HydroObject,
    ObjectType,
)
from hydropilot_api.main import app

client = TestClient(app)


class ConstraintRepository:
    def __init__(self):
        self.objects = {
            "reservoir-alpha": HydroObject(
                id="reservoir-alpha",
                name="Reservoir Alpha",
                object_type=ObjectType.RESERVOIR,
                geometry=Geometry(type="Point", coordinates=[-122.0, 40.0]),
            )
        }
        self.constraints = [
            HydroConstraint(
                id="constraint-max-level",
                object_id="reservoir-alpha",
                variable="level",
                constraint_type=ConstraintType.MAXIMUM,
                unit="m",
                max_value=325.0,
                active_when={"season": "flood"},
                source="test-rulebook",
            ),
            HydroConstraint(
                id="constraint-min-release",
                object_id="reservoir-alpha",
                variable="release",
                constraint_type=ConstraintType.MINIMUM,
                unit="m3/s",
                min_value=20.0,
                source="test-rulebook",
            ),
        ]
        self.last_constraint_filter = None

    def get_object(self, object_id):
        return self.objects.get(object_id)

    def list_constraints(self, object_id=None, variable=None):
        self.last_constraint_filter = (object_id, variable)
        values = self.constraints
        if object_id is not None:
            values = [item for item in values if item.object_id == object_id]
        if variable is not None:
            values = [item for item in values if item.variable == variable]
        return sorted(values, key=lambda item: item.id)


def test_sacramento_reservoir_constraints_are_honestly_empty():
    response = client.get("/api/objects/reservoir-shasta/constraints")

    assert response.status_code == 200
    assert response.json() == []


def test_object_constraints_endpoint_preserves_semantics_and_provenance(monkeypatch):
    repo = ConstraintRepository()
    monkeypatch.setattr(main_module, "repo", lambda: repo)

    response = client.get("/api/objects/reservoir-alpha/constraints")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == ["constraint-max-level", "constraint-min-release"]
    maximum = body[0]
    assert maximum["variable"] == "level"
    assert maximum["constraint_type"] == "maximum"
    assert maximum["unit"] == "m"
    assert maximum["max_value"] == 325.0
    assert maximum["active_when"] == {"season": "flood"}
    assert maximum["source"] == "test-rulebook"


def test_object_constraints_endpoint_forwards_variable_filter(monkeypatch):
    repo = ConstraintRepository()
    monkeypatch.setattr(main_module, "repo", lambda: repo)

    response = client.get(
        "/api/objects/reservoir-alpha/constraints",
        params={"variable": "release"},
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["constraint-min-release"]
    assert repo.last_constraint_filter == ("reservoir-alpha", "release")


def test_object_constraints_endpoint_returns_404_for_missing_object(monkeypatch):
    repo = ConstraintRepository()
    monkeypatch.setattr(main_module, "repo", lambda: repo)

    response = client.get("/api/objects/reservoir-missing/constraints")

    assert response.status_code == 404
    assert response.json() == {"detail": "object not found"}
