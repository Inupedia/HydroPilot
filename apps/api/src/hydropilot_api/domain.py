from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal
from pydantic import BaseModel, Field


class ObjectType(StrEnum):
    RIVER_REACH = "river_reach"
    RESERVOIR = "reservoir"
    DAM = "dam"
    GAUGE = "gauge"
    CONTROL_POINT = "control_point"


class RelationType(StrEnum):
    FLOWS_TO = "FLOWS_TO"
    LOCATED_ON = "LOCATED_ON"
    IMPOUNDS = "IMPOUNDS"
    MONITORS = "MONITORS"
    CONTROLS = "CONTROLS"
    DISCHARGES_TO = "DISCHARGES_TO"


class Geometry(BaseModel):
    type: Literal["Point", "LineString", "Polygon"]
    coordinates: Any


class HydroObject(BaseModel):
    id: str
    name: str
    object_type: ObjectType
    geometry: Geometry
    properties: dict[str, Any] = Field(default_factory=dict)
    source: str = "fixture"


class HydroRelation(BaseModel):
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    properties: dict[str, Any] = Field(default_factory=dict)


class Scenario(BaseModel):
    id: str
    name: str
    mode: Literal["CURRENT", "SCENARIO"] = "SCENARIO"


class HydroState(BaseModel):
    scenario_id: str
    object_id: str
    timestamp_minutes: int
    variable: str
    value: float
    unit: str


class NetworkPathItem(BaseModel):
    object_id: str
    hop: int
    via_relation: RelationType = RelationType.FLOWS_TO
