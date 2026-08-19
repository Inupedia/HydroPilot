from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from hydropilot_core.runoff import (
    LinearReservoirParameters,
    LinearReservoirState,
    step_linear_reservoir,
    total_flow_cms,
)


class RainfallForecastPoint(BaseModel):
    timestamp_minutes: int = Field(gt=0)
    precipitation_mm: float = Field(ge=0)


class RunoffForecastRequest(BaseModel):
    object_id: str
    rainfall: list[RainfallForecastPoint] = Field(min_length=1)
    dt_minutes: int = Field(default=60, gt=0, le=360)
    initial_flow_cms: float = Field(ge=0)
    catchment_area_km2: float = Field(gt=0)
    runoff_coefficient: float = Field(default=0.45, ge=0, le=1)
    response_time_hours: float = Field(default=6.0, gt=0, le=240)
    baseflow_cms: float = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_time_grid_and_baseflow(self) -> "RunoffForecastRequest":
        expected = self.dt_minutes
        for point in self.rainfall:
            if point.timestamp_minutes != expected:
                raise ValueError("rainfall timestamps must follow a contiguous dt_minutes grid starting at dt_minutes")
            expected += self.dt_minutes
        if self.baseflow_cms > self.initial_flow_cms:
            raise ValueError("baseflow_cms cannot exceed initial_flow_cms")
        return self


class RunoffForecastPoint(BaseModel):
    timestamp_minutes: int = Field(gt=0)
    rainfall_mm: float = Field(ge=0)
    flow_cms: float = Field(ge=0)


class RunoffForecastSummary(BaseModel):
    current_flow_cms: float = Field(ge=0)
    peak_flow_cms: float = Field(ge=0)
    peak_timestamp_minutes: int = Field(gt=0)
    peak_change_pct: float | None = None
    total_rainfall_mm: float = Field(ge=0)


class RunoffForecastResponse(BaseModel):
    object_id: str
    model: str = "linear_reservoir"
    dt_minutes: int
    horizon_minutes: int
    runoff: list[RunoffForecastPoint]
    summary: RunoffForecastSummary


def run_runoff_forecast(request: RunoffForecastRequest) -> RunoffForecastResponse:
    params = LinearReservoirParameters(
        catchment_area_km2=request.catchment_area_km2,
        runoff_coefficient=request.runoff_coefficient,
        response_time_hours=request.response_time_hours,
        baseflow_cms=request.baseflow_cms,
    )
    state = LinearReservoirState(
        quickflow_cms=max(request.initial_flow_cms - request.baseflow_cms, 0.0)
    )
    runoff: list[RunoffForecastPoint] = []

    for rainfall in request.rainfall:
        state = step_linear_reservoir(
            state,
            rainfall.precipitation_mm,
            dt_minutes=request.dt_minutes,
            params=params,
        )
        runoff.append(
            RunoffForecastPoint(
                timestamp_minutes=rainfall.timestamp_minutes,
                rainfall_mm=rainfall.precipitation_mm,
                flow_cms=total_flow_cms(state, params),
            )
        )

    peak = max(runoff, key=lambda point: point.flow_cms)
    peak_change_pct = None
    if request.initial_flow_cms > 0:
        peak_change_pct = ((peak.flow_cms - request.initial_flow_cms) / request.initial_flow_cms) * 100.0

    return RunoffForecastResponse(
        object_id=request.object_id,
        dt_minutes=request.dt_minutes,
        horizon_minutes=request.rainfall[-1].timestamp_minutes,
        runoff=runoff,
        summary=RunoffForecastSummary(
            current_flow_cms=request.initial_flow_cms,
            peak_flow_cms=peak.flow_cms,
            peak_timestamp_minutes=peak.timestamp_minutes,
            peak_change_pct=peak_change_pct,
            total_rainfall_mm=sum(point.precipitation_mm for point in request.rainfall),
        ),
    )
