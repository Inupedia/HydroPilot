from __future__ import annotations

import math

from pydantic import BaseModel, Field


class LinearReservoirParameters(BaseModel):
    catchment_area_km2: float = Field(gt=0)
    runoff_coefficient: float = Field(ge=0, le=1)
    response_time_hours: float = Field(gt=0)
    baseflow_cms: float = Field(default=0, ge=0)


class LinearReservoirState(BaseModel):
    quickflow_cms: float = Field(default=0, ge=0)


def rainfall_input_cms(
    rainfall_mm: float,
    *,
    dt_minutes: float,
    params: LinearReservoirParameters,
) -> float:
    if rainfall_mm < 0:
        raise ValueError("rainfall_mm cannot be negative")
    if dt_minutes <= 0:
        raise ValueError("dt_minutes must be positive")

    effective_depth_m = (rainfall_mm / 1000.0) * params.runoff_coefficient
    area_m2 = params.catchment_area_km2 * 1_000_000.0
    volume_m3 = effective_depth_m * area_m2
    return volume_m3 / (dt_minutes * 60.0)


def step_linear_reservoir(
    state: LinearReservoirState,
    rainfall_mm: float,
    *,
    dt_minutes: float,
    params: LinearReservoirParameters,
) -> LinearReservoirState:
    rainfall_cms = rainfall_input_cms(rainfall_mm, dt_minutes=dt_minutes, params=params)
    response_minutes = params.response_time_hours * 60.0
    decay = math.exp(-dt_minutes / response_minutes)
    quickflow = state.quickflow_cms * decay + rainfall_cms * (1.0 - decay)
    return LinearReservoirState(quickflow_cms=max(quickflow, 0.0))


def total_flow_cms(state: LinearReservoirState, params: LinearReservoirParameters) -> float:
    return params.baseflow_cms + state.quickflow_cms
