from __future__ import annotations

import json
import sys
from pathlib import Path

VALID_OBJECT_TYPES = {"river_reach", "reservoir", "dam", "gauge", "control_point"}
VALID_RELATIONS = {"FLOWS_TO", "LOCATED_ON", "IMPOUNDS", "MONITORS", "CONTROLS", "DISCHARGES_TO"}


def load_fixture(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_fixture(data: dict) -> list[str]:
    errors: list[str] = []
    objects = data.get("objects", [])
    relations = data.get("relations", [])
    object_ids = {obj.get("id") for obj in objects}

    if not 20 <= len([o for o in objects if o.get("object_type") == "river_reach"]) <= 200:
        errors.append("fixture must contain 20-200 river reaches")

    for obj in objects:
        if obj.get("object_type") not in VALID_OBJECT_TYPES:
            errors.append(f"invalid object_type: {obj.get('id')}")
        if obj.get("geometry", {}).get("type") not in {"Point", "LineString", "Polygon"}:
            errors.append(f"invalid geometry type: {obj.get('id')}")

    for rel in relations:
        if rel.get("relation_type") not in VALID_RELATIONS:
            errors.append(f"invalid relation_type: {rel.get('id')}")
        if rel.get("source_id") not in object_ids or rel.get("target_id") not in object_ids:
            errors.append(f"relation references missing object: {rel.get('id')}")

    return errors


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/demo/sacramento_v0_1.json")
    errors = validate_fixture(load_fixture(path))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"Fixture OK: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
