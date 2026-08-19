from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from hydropilot_api.repositories.protocols import HydroRepository
from hydropilot_api.services.runoff_forecast import (
    RainfallForecastPoint,
    RunoffForecastRequest,
    RunoffForecastResponse,
    run_runoff_forecast,
)
from hydropilot_api.services.scenario import (
    HydrographPoint,
    ReleaseScenarioRequest,
    ReleaseScenarioResponse,
    run_release_scenario,
)


class ReservoirRainfallForecastRequest(BaseModel):
    reservoir_id: str = "reservoir-shasta"
    rainfall: list[RainfallForecastPoint] = Field(min_length=1)
    dt_minutes: int = Field(default=30, gt=0, le=240)
    initial_inflow_cms: float = Field(ge=0)
    release_cms: float = Field(ge=0)
    catchment_area_km2: float = Field(gt=0)
    runoff_coefficient: float = Field(default=0.18, ge=0, le=1)
    response_time_hours: float = Field(default=8.0, gt=0, le=240)
    baseflow_cms: float = Field(default=0, ge=0)
    max_hops: int = Field(default=6, ge=1, le=12)

    @model_validator(mode="after")
    def validate_forecast_horizon(self) -> "ReservoirRainfallForecastRequest":
        if self.rainfall[-1].timestamp_minutes > 1440:
            raise ValueError("reservoir rainfall forecast horizon cannot exceed 1440 minutes")
        return self


class ReservoirForecastSummary(BaseModel):
    current_storage_m3: float = Field(ge=0)
    final_storage_m3: float = Field(ge=0)
    min_storage_m3: float = Field(ge=0)
    max_storage_m3: float = Field(ge=0)
    storage_change_m3: float
    storage_change_pct: float | None = None
    peak_inflow_cms: float = Field(ge=0)
    peak_inflow_timestamp_minutes: int = Field(gt=0)
    release_cms: float = Field(ge=0)
    final_level_m: float | None = None


class ReservoirRainfallForecastResponse(BaseModel):
    reservoir_id: str
    model: str = "rainfall_runoff_plus_reservoir_balance"
    runoff: RunoffForecastResponse
    scenario: ReleaseScenarioResponse
    summary: ReservoirForecastSummary


def run_reservoir_rainfall_forecast(
    repo: HydroRepository,
    request: ReservoirRainfallForecastRequest,
) -> ReservoirRainfallForecastResponse:
    runoff = run_runoff_forecast(
        RunoffForecastRequest(
            object_id=request.reservoir_id,
            rainfall=request.rainfall,
            dt_minutes=request.dt_minutes,
            initial_flow_cms=request.initial_inflow_cms,
            catchment_area_km2=request.catchment_area_km2,
            runoff_coefficient=request.runoff_coefficient,
            response_time_hours=request.response_time_hours,
            baseflow_cms=request.baseflow_cms,
        )
    )

    duration_minutes = runoff.horizon_minutes
    inflow_hydrograph = [
        HydrographPoint(timestamp_minutes=0, flow_cms=request.initial_inflow_cms),
        *[
            HydrographPoint(timestamp_minutes=point.timestamp_minutes, flow_cms=point.flow_cms)
            for point in runoff.runoff
        ],
    ]
    release_hydrograph = [
        HydrographPoint(timestamp_minutes=0, flow_cms=request.release_cms),
        HydrographPoint(timestamp_minutes=duration_minutes, flow_cms=request.release_cms),
    ]
    scenario = run_release_scenario(
        repo,
        ReleaseScenarioRequest(
            reservoir_id=request.reservoir_id,
            duration_minutes=duration_minutes,
            dt_minutes=request.dt_minutes,
            max_hops=request.max_hops,
            inflow_hydrograph=inflow_hydrograph,
            release_hydrograph=release_hydrograph,
        ),
    )

    storage_states = sorted(
        [
            state
            for state in scenario.states
            if state.object_id == request.reservoir_id and state.variable == "storage"
        ],
        key=lambda state: state.timestamp_minutes,
    )
    if not storage_states:
        raise ValueError("reservoir forecast scenario did not produce storage states")

    current_storage = storage_states[0].value
    final_storage = storage_states[-1].value
    storage_change = final_storage - current_storage
    storage_change_pct = None
    if current_storage > 0:
        storage_change_pct = (storage_change / current_storage) * 100.0

    final_level = next(
        (
            state.value
            for state in scenario.states
            if state.object_id == request.reservoir_id
            and state.variable == "level"
            and state.timestamp_minutes == duration_minutes
        ),
        None,
    )

    return ReservoirRainfallForecastResponse(
        reservoir_id=request.reservoir_id,
        runoff=runoff,
        scenario=scenario,
        summary=ReservoirForecastSummary(
            current_storage_m3=current_storage,
            final_storage_m3=final_storage,
            min_storage_m3=min(state.value for state in storage_states),
            max_storage_m3=max(state.value for state in storage_states),
            storage_change_m3=storage_change,
            storage_change_pct=storage_change_pct,
            peak_inflow_cms=runoff.summary.peak_flow_cms,
            peak_inflow_timestamp_minutes=runoff.summary.peak_timestamp_minutes,
            release_cms=request.release_cms,
            final_level_m=final_level,
        ),
    )
