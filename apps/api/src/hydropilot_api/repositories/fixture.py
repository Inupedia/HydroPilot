from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from .protocols import HydroRepository
from hydropilot_api.domain import HydroObject, HydroRelation, ObjectType


class FixtureHydroRepository(HydroRepository):
    def __init__(self, fixture_path: Path):
        self.fixture_path = fixture_path
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        self.objects = [HydroObject.model_validate(item) for item in data["objects"]]
        self.relations = [HydroRelation.model_validate(item) for item in data["relations"]]

    def list_objects(self, object_type: ObjectType | None = None) -> list[HydroObject]:
        values = self.objects if object_type is None else [obj for obj in self.objects if obj.object_type == object_type]
        return sorted(values, key=lambda item: item.id)

    def get_object(self, object_id: str) -> HydroObject | None:
        return next((obj for obj in self.objects if obj.id == object_id), None)

    def list_relations(self) -> list[HydroRelation]:
        return self.relations


@lru_cache
def get_fixture_repository(fixture_path: str) -> FixtureHydroRepository:
    return FixtureHydroRepository(Path(fixture_path))
