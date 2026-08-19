from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from .protocols import HydroRepository
from hydropilot_api.domain import CurveType, HydroCurve, HydroObject, HydroRelation, ObjectType


class FixtureHydroRepository(HydroRepository):
    def __init__(self, fixture_path: Path):
        self.fixture_path = fixture_path
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        self.objects = [HydroObject.model_validate(item) for item in data["objects"]]
        self.relations = [HydroRelation.model_validate(item) for item in data["relations"]]
        self.curves = [HydroCurve.model_validate(item) for item in data.get("curves", [])]

    def list_objects(self, object_type: ObjectType | None = None) -> list[HydroObject]:
        values = self.objects if object_type is None else [obj for obj in self.objects if obj.object_type == object_type]
        return sorted(values, key=lambda item: item.id)

    def get_object(self, object_id: str) -> HydroObject | None:
        return next((obj for obj in self.objects if obj.id == object_id), None)

    def list_relations(self) -> list[HydroRelation]:
        return self.relations

    def list_curves(
        self,
        object_id: str | None = None,
        curve_type: CurveType | None = None,
    ) -> list[HydroCurve]:
        values = self.curves
        if object_id is not None:
            values = [curve for curve in values if curve.object_id == object_id]
        if curve_type is not None:
            values = [curve for curve in values if curve.curve_type is curve_type]
        return sorted(values, key=lambda curve: curve.id)


@lru_cache
def get_fixture_repository(fixture_path: str) -> FixtureHydroRepository:
    return FixtureHydroRepository(Path(fixture_path))
