from __future__ import annotations

from pydantic import BaseModel, Field
from hydropilot_core.reservoir import ReservoirState, ReservoirStep, step_reservoir
from hydropilot_core.routing import MuskingumParameters, route_muskingum
from hydropilot_api.domain import HydroState
from hydropilot_api.repositories.protocols import HydroRepository
from hydropilot_api.topology import downstream_path


class ReleaseScenarioRequest(BaseModel):
    reservoir_id: str = "reservoir-shasta"
    release_cms: float = Field(gt=0)
    duration_minutes: int = Field(default=180, gt=0, le=1440)
    dt_minutes: int = Field(default=30, gt=0, le=240)
    max_hops: int = Field(default=4, ge=1, le=12)


class ReleaseScenarioResponse(BaseModel):
    scenario_id: str
    states: list[HydroState]


def run_release_scenario(repo: HydroRepository, request: ReleaseScenarioRequest) -> ReleaseScenarioResponse:
    reservoir = repo.get_object(request.reservoir_id)
    if reservoir is None:
        raise KeyError(request.reservoir_id)
    storage = float(reservoir.properties.get("initial_storage_m3", 0))
    max_storage = float(reservoir.properties.get("max_storage_m3", max(storage, 1)))
    level = reservoir.properties.get("initial_level_m")
    state = ReservoirState(storage_m3=storage, max_storage_m3=max_storage, level_m=float(level) if level is not None else None)
    downstream = downstream_path("reach-001", repo.list_relations(), max_hops=request.max_hops)
    timestamps = list(range(0, request.duration_minutes + request.dt_minutes, request.dt_minutes))
    inflow_series = [request.release_cms for _ in timestamps]
    states: list[HydroState] = []

    for timestamp in timestamps:
        if timestamp > 0:
            state = step_reservoir(state, ReservoirStep(inflow_cms=request.release_cms * 0.6, outflow_cms=request.release_cms, dt_seconds=request.dt_minutes * 60))
        states.append(HydroState(scenario_id="scenario-release", object_id=request.reservoir_id, timestamp_minutes=timestamp, variable="storage", value=state.storage_m3, unit="m3"))
        if state.level_m is not None:
            states.append(HydroState(scenario_id="scenario-release", object_id=request.reservoir_id, timestamp_minutes=timestamp, variable="level", value=state.level_m, unit="m"))

    for idx, item in enumerate(downstream, start=1):
        params = MuskingumParameters(k_seconds=(1800 + idx * 600), x=0.2, dt_seconds=request.dt_minutes * 60)
        routed = route_muskingum(inflow_series, params)
        for timestamp, flow in zip(timestamps, routed, strict=True):
            states.append(HydroState(scenario_id="scenario-release", object_id=item.object_id, timestamp_minutes=timestamp, variable="flow", value=flow, unit="m3/s"))

    return ReleaseScenarioResponse(scenario_id="scenario-release", states=states)
