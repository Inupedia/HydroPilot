from __future__ import annotations

from typing import Protocol
from hydropilot_api.domain import CurveType, HydroCurve, HydroObject, HydroRelation, ObjectType


class HydroRepository(Protocol):
    def list_objects(self, object_type: ObjectType | None = None) -> list[HydroObject]: ...
    def get_object(self, object_id: str) -> HydroObject | None: ...
    def list_relations(self) -> list[HydroRelation]: ...
    def list_curves(
        self,
        object_id: str | None = None,
        curve_type: CurveType | None = None,
    ) -> list[HydroCurve]: ...
