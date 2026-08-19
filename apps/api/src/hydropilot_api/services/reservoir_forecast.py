from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from hydropilot_api.domain import HydroState, RelationType
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
    release_response_fraction: float = Field(default=0, ge=0, le=1)
    max_release_cms: float | None = Field(default=None, ge=0)
    catchment_area_km2: float = Field(gt=0)
    runoff_coefficient: float = Field(default=0.18, ge=0, le=1)
    response_time_hours: float = Field(default=8.0, gt=0, le=240)
    baseflow_cms: float = Field(default=0, ge=0)
    max_hops: int = Field(default=20, ge=1, le=25)

    @model_validator(mode="after")
    def validate_forecast_horizon(self) -> "ReservoirRainfallForecastRequest":
        if self.rainfall[-1].timestamp_minutes > 1440:
            raise ValueError("reservoir rainfall forecast horizon cannot exceed 1440 minutes")
        if self.max_release_cms is not None and self.max_release_cms < self.release_cms:
            raise ValueError("max_release_cms cannot be lower than release_cms")
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
    peak_release_cms: float = Field(ge=0)
    release_response_fraction: float = Field(ge=0, le=1)
    final_level_m: float | None = None


class ReservoirRainfallForecastResponse(BaseModel):
    reservoir_id: str
    model: str = "rainfall_runoff_plus_reservoir_balance"
    runoff: RunoffForecastResponse
    scenario: ReleaseScenarioResponse
    summary: ReservoirForecastSummary


class _ReservoirForecastScenarioRequest(ReleaseScenarioRequest):
    """Internal scenario contract that allows a forecast to cover a longer routing chain."""

    max_hops: int = Field(default=20, ge=1, le=25)


def _forecast_release_hydrograph(
    request: ReservoirRainfallForecastRequest,
    runoff: RunoffForecastResponse,
) -> list[HydrographPoint]:
    points = [HydrographPoint(timestamp_minutes=0, flow_cms=request.release_cms)]
    for runoff_point in runoff.runoff:
        excess_inflow = max(0.0, runoff_point.flow_cms - request.initial_inflow_cms)
        release = request.release_cms + request.release_response_fraction * excess_inflow
        if request.max_release_cms is not None:
            release = min(release, request.max_release_cms)
        points.append(
            HydrographPoint(
                timestamp_minutes=runoff_point.timestamp_minutes,
                flow_cms=release,
            )
        )
    return points


def _project_control_point_flow_states(
    repo: HydroRepository,
    scenario: ReleaseScenarioResponse,
) -> ReleaseScenarioResponse:
    states = list(scenario.states)
    existing = {
        (state.object_id, state.variable, state.timestamp_minutes)
        for state in states
    }
    flow_states_by_object: dict[str, list[HydroState]] = {}
    for state in states:
        if state.variable == "flow":
            flow_states_by_object.setdefault(state.object_id, []).append(state)

    for relation in repo.list_relations():
        if relation.relation_type is not RelationType.CONTROLS:
            continue
        source_states = flow_states_by_object.get(relation.source_id, [])
        if not source_states:
            continue
        if repo.get_object(relation.target_id) is None:
            raise ValueError(f"controlled object not found: {relation.target_id}")
        for source_state in source_states:
            key = (relation.target_id, "flow", source_state.timestamp_minutes)
            if key in existing:
                continue
            states.append(
                HydroState(
                    scenario_id=source_state.scenario_id,
                    object_id=relation.target_id,
                    timestamp_minutes=source_state.timestamp_minutes,
                    variable="flow",
                    value=source_state.value,
                    unit=source_state.unit,
                )
            )
            existing.add(key)

    return scenario.model_copy(update={"states": states})


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
    release_hydrograph = _forecast_release_hydrograph(request, runoff)
    scenario = run_release_scenario(
        repo,
        _ReservoirForecastScenarioRequest(
            reservoir_id=request.reservoir_id,
            duration_minutes=duration_minutes,
            dt_minutes=request.dt_minutes,
            max_hops=request.max_hops,
            inflow_hydrograph=inflow_hydrograph,
            release_hydrograph=release_hydrograph,
        ),
    )
    scenario = _project_control_point_flow_states(repo, scenario)

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

    release_states = sorted(
        [
            state
            for state in scenario.states
            if state.object_id == request.reservoir_id and state.variable == "release"
        ],
        key=lambda state: state.timestamp_minutes,
    )
    if not release_states:
        raise ValueError("reservoir forecast scenario did not produce release states")

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
            peak_release_cms=max(state.value for state in release_states),
            release_response_fraction=request.release_response_fraction,
            final_level_m=final_level,
        ),
    )
