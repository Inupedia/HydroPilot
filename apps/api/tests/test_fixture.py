import json
from pathlib import Path

from hydropilot_api.domain import CurveType
from hydropilot_api.repositories.fixture import FixtureHydroRepository
from scripts.check_fixture import load_fixture, validate_fixture


def test_sacramento_fixture_is_valid_and_has_no_synthetic_curves():
    fixture_path = Path(__file__).resolve().parents[3] / "data" / "demo" / "sacramento_v0_1.json"
    errors = validate_fixture(load_fixture(fixture_path))
    assert errors == []

    repo = FixtureHydroRepository(fixture_path)
    assert repo.list_curves() == []


def test_fixture_repository_parses_and_filters_curves(tmp_path: Path):
    fixture_path = tmp_path / "curves.json"
    fixture_path.write_text(
        json.dumps(
            {
                "objects": [
                    {
                        "id": "reservoir-alpha",
                        "name": "Reservoir Alpha",
                        "object_type": "reservoir",
                        "geometry": {"type": "Point", "coordinates": [-122.0, 40.0]},
                        "properties": {},
                    },
                    {
                        "id": "gate-alpha",
                        "name": "Gate Alpha",
                        "object_type": "gate",
                        "geometry": {"type": "Point", "coordinates": [-122.0, 40.0]},
                        "properties": {},
                    },
                ],
                "relations": [],
                "curves": [
                    {
                        "id": "curve-level-storage",
                        "object_id": "reservoir-alpha",
                        "curve_type": "level_storage",
                        "x_unit": "m",
                        "y_unit": "m3",
                        "points": [{"x": 100.0, "y": 1_000_000.0}, {"x": 110.0, "y": 1_200_000.0}],
                        "source": "test",
                    },
                    {
                        "id": "curve-level-area",
                        "object_id": "reservoir-alpha",
                        "curve_type": "level_area",
                        "x_unit": "m",
                        "y_unit": "m2",
                        "points": [{"x": 100.0, "y": 50_000.0}, {"x": 110.0, "y": 60_000.0}],
                        "source": "test",
                    },
                    {
                        "id": "curve-gate-discharge",
                        "object_id": "gate-alpha",
                        "curve_type": "gate_opening_discharge",
                        "x_unit": "m",
                        "y_unit": "m3/s",
                        "points": [{"x": 0.5, "y": 20.0}, {"x": 1.0, "y": 50.0}],
                        "source": "test",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    repo = FixtureHydroRepository(fixture_path)

    assert [curve.id for curve in repo.list_curves()] == [
        "curve-gate-discharge",
        "curve-level-area",
        "curve-level-storage",
    ]
    assert [curve.id for curve in repo.list_curves(object_id="reservoir-alpha")] == [
        "curve-level-area",
        "curve-level-storage",
    ]
    assert [
        curve.id
        for curve in repo.list_curves(
            object_id="reservoir-alpha",
            curve_type=CurveType.LEVEL_STORAGE,
        )
    ] == ["curve-level-storage"]
