from __future__ import annotations

import json
from pathlib import Path
from check_fixture import validate_fixture


def build_insert_summary(path: Path) -> dict[str, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_fixture(data)
    if errors:
        raise ValueError("; ".join(errors))
    return {"objects": len(data["objects"]), "relations": len(data["relations"])}


if __name__ == "__main__":
    print(build_insert_summary(Path("data/demo/sacramento_v0_1.json")))
