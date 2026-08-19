from fastapi.testclient import TestClient

import hydropilot_api.main as main_module
from hydropilot_api.domain import (
    CurveType,
    Geometry,
    HydroCurve,
    HydroCurvePoint,
    HydroObject,
    ObjectType,
)
from hydropilot_api.main import app

client = TestClient(app)


class CurveRepository:
    def __init__(self):
        self.objects = {
            "reservoir-alpha": HydroObject(
                id="reservoir-alpha",
                name="Reservoir Alpha",
                object_type=ObjectType.RESERVOIR,
                geometry=Geometry(type="Point", coordinates=[-122.0, 40.0]),
            )
        }
        self.curves = [
            HydroCurve(
                id="curve-level-storage",
                object_id="reservoir-alpha",
                curve_type=CurveType.LEVEL_STORAGE,
                x_unit="m",
                y_unit="m3",
                points=[
                    HydroCurvePoint(x=100.0, y=1_000_000.0),
                    HydroCurvePoint(x=110.0, y=1_200_000.0),
                ],
                source="test-engineering-source",
            ),
            HydroCurve(
                id="curve-level-area",
                object_id="reservoir-alpha",
                curve_type=CurveType.LEVEL_AREA,
                x_unit="m",
                y_unit="m2",
                points=[
                    HydroCurvePoint(x=100.0, y=50_000.0),
                    HydroCurvePoint(x=110.0, y=60_000.0),
                ],
                source="test-engineering-source",
            ),
        ]
        self.last_curve_filter = None

    def get_object(self, object_id):
        return self.objects.get(object_id)

    def list_curves(self, object_id=None, curve_type=None):
        self.last_curve_filter = (object_id, curve_type)
        values = self.curves
        if object_id is not None:
            values = [curve for curve in values if curve.object_id == object_id]
        if curve_type is not None:
            values = [curve for curve in values if curve.curve_type is curve_type]
        return sorted(values, key=lambda curve: curve.id)


def test_sacramento_reservoir_curves_are_honestly_empty():
    response = client.get("/api/objects/reservoir-shasta/curves")

    assert response.status_code == 200
    assert response.json() == []


def test_object_curves_endpoint_returns_domain_curve_with_provenance(monkeypatch):
    repo = CurveRepository()
    monkeypatch.setattr(main_module, "repo", lambda: repo)

    response = client.get("/api/objects/reservoir-alpha/curves")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == ["curve-level-area", "curve-level-storage"]
    storage = next(item for item in body if item["id"] == "curve-level-storage")
    assert storage["curve_type"] == "level_storage"
    assert storage["x_unit"] == "m"
    assert storage["y_unit"] == "m3"
    assert storage["source"] == "test-engineering-source"
    assert storage["points"] == [
        {"x": 100.0, "y": 1_000_000.0},
        {"x": 110.0, "y": 1_200_000.0},
    ]


def test_object_curves_endpoint_forwards_typed_curve_filter(monkeypatch):
    repo = CurveRepository()
    monkeypatch.setattr(main_module, "repo", lambda: repo)

    response = client.get(
        "/api/objects/reservoir-alpha/curves",
        params={"curve_type": "level_storage"},
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["curve-level-storage"]
    assert repo.last_curve_filter == ("reservoir-alpha", CurveType.LEVEL_STORAGE)


def test_object_curves_endpoint_returns_404_for_missing_object(monkeypatch):
    repo = CurveRepository()
    monkeypatch.setattr(main_module, "repo", lambda: repo)

    response = client.get("/api/objects/reservoir-missing/curves")

    assert response.status_code == 404
    assert response.json() == {"detail": "object not found"}
