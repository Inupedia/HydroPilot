import json
from pathlib import Path

from hydropilot_api.repositories.fixture import FixtureHydroRepository


def test_sacramento_fixture_has_no_synthetic_constraints():
    fixture_path = Path(__file__).resolve().parents[3] / "data" / "demo" / "sacramento_v0_1.json"

    repo = FixtureHydroRepository(fixture_path)

    assert repo.list_constraints() == []


def test_fixture_repository_parses_and_filters_constraints(tmp_path: Path):
    fixture_path = tmp_path / "constraints.json"
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
                        "id": "outlet-alpha",
                        "name": "Outlet Alpha",
                        "object_type": "outlet",
                        "geometry": {"type": "Point", "coordinates": [-122.0, 40.0]},
                        "properties": {},
                    },
                ],
                "relations": [],
                "constraints": [
                    {
                        "id": "constraint-max-level",
                        "object_id": "reservoir-alpha",
                        "variable": "level",
                        "constraint_type": "maximum",
                        "unit": "m",
                        "max_value": 325.0,
                        "active_when": {"season": "flood"},
                        "source": "test-rulebook",
                    },
                    {
                        "id": "constraint-level-range",
                        "object_id": "reservoir-alpha",
                        "variable": "level",
                        "constraint_type": "range",
                        "unit": "m",
                        "min_value": 250.0,
                        "max_value": 325.0,
                        "source": "test-rulebook",
                    },
                    {
                        "id": "constraint-min-release",
                        "object_id": "outlet-alpha",
                        "variable": "release",
                        "constraint_type": "minimum",
                        "unit": "m3/s",
                        "min_value": 20.0,
                        "source": "test-rulebook",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    repo = FixtureHydroRepository(fixture_path)

    assert [item.id for item in repo.list_constraints()] == [
        "constraint-level-range",
        "constraint-max-level",
        "constraint-min-release",
    ]
    assert [item.id for item in repo.list_constraints(object_id="reservoir-alpha")] == [
        "constraint-level-range",
        "constraint-max-level",
    ]
    assert [
        item.id
        for item in repo.list_constraints(
            object_id="reservoir-alpha",
            variable="level",
        )
    ] == ["constraint-level-range", "constraint-max-level"]
