from pathlib import Path
from scripts.check_fixture import load_fixture, validate_fixture


def test_sacramento_fixture_is_valid():
    fixture_path = Path(__file__).resolve().parents[3] / "data" / "demo" / "sacramento_v0_1.json"
    errors = validate_fixture(load_fixture(fixture_path))
    assert errors == []
