from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ObjectType(StrEnum):
    RIVER_REACH = "river_reach"
    RESERVOIR = "reservoir"
    DAM = "dam"
    GAUGE = "gauge"
    CONTROL_POINT = "control_point"
    CHANNEL = "channel"
    TUNNEL = "tunnel"
    AQUEDUCT = "aqueduct"
    SIPHON = "siphon"
    PUMP_STATION = "pump_station"
    GATE = "gate"
    DIVERSION = "diversion"
    INTAKE = "intake"
    POWERHOUSE = "powerhouse"
    SPILLWAY = "spillway"
    OUTLET = "outlet"
    FLOOD_STORAGE = "flood_storage"
    LEVEE = "levee"
    WATER_USE_UNIT = "water_use_unit"
    IRRIGATION_DISTRICT = "irrigation_district"
    CONTROL_SECTION = "control_section"


class RelationType(StrEnum):
    FLOWS_TO = "FLOWS_TO"
    LOCATED_ON = "LOCATED_ON"
    IMPOUNDS = "IMPOUNDS"
    MONITORS = "MONITORS"
    CONTROLS = "CONTROLS"
    DISCHARGES_TO = "DISCHARGES_TO"
    CONVEYS_TO = "CONVEYS_TO"
    DIVERTS_TO = "DIVERTS_TO"
    REGULATES = "REGULATES"
    SERVES = "SERVES"
    BELONGS_TO = "BELONGS_TO"


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


class CurveType(StrEnum):
    LEVEL_STORAGE = "level_storage"
    LEVEL_AREA = "level_area"
    LEVEL_DISCHARGE = "level_discharge"
    GATE_OPENING_DISCHARGE = "gate_opening_discharge"


class HydroCurvePoint(BaseModel):
    x: float
    y: float


class HydroCurve(BaseModel):
    id: str
    object_id: str
    curve_type: CurveType
    x_unit: str
    y_unit: str
    points: list[HydroCurvePoint] = Field(min_length=2)
    source: str = "fixture"

    @model_validator(mode="after")
    def points_must_be_strictly_increasing(self) -> "HydroCurve":
        if any(current.x >= following.x for current, following in zip(self.points, self.points[1:])):
            raise ValueError("curve x-values must be strictly increasing")
        return self


class ConstraintType(StrEnum):
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    RANGE = "range"
    RAMP_RATE = "ramp_rate"


class HydroConstraint(BaseModel):
    id: str
    object_id: str
    variable: str
    constraint_type: ConstraintType
    unit: str
    min_value: float | None = None
    max_value: float | None = None
    active_when: dict[str, Any] = Field(default_factory=dict)
    source: str = "fixture"

    @model_validator(mode="after")
    def bounds_match_constraint_type(self) -> "HydroConstraint":
        if self.constraint_type is ConstraintType.MINIMUM and self.min_value is None:
            raise ValueError("minimum constraint requires min_value")
        if self.constraint_type is ConstraintType.MAXIMUM and self.max_value is None:
            raise ValueError("maximum constraint requires max_value")
        if self.constraint_type is ConstraintType.RANGE:
            if self.min_value is None or self.max_value is None:
                raise ValueError("range constraint requires min_value and max_value")
            if self.min_value > self.max_value:
                raise ValueError("range constraint min_value cannot exceed max_value")
        if self.constraint_type is ConstraintType.RAMP_RATE and self.max_value is None:
            raise ValueError("ramp-rate constraint requires max_value")
        return self


class HydroRule(BaseModel):
    id: str
    name: str
    object_id: str | None = None
    priority: int = Field(default=100, ge=0)
    condition: dict[str, Any]
    action: dict[str, Any]
    source: str = "manual"


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
