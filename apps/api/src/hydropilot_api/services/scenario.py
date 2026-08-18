from __future__ import annotations

from pydantic import BaseModel, Field
from hydropilot_core.reservoir import ReservoirState, ReservoirStep, step_reservoir
from hydropilot_core.routing import MuskingumParameters, route_muskingum
from hydropilot_api.domain import HydroRelation, HydroState, RelationType
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


def _release_reach_id(reservoir_id: str, relations: list[HydroRelation]) -> str:
    targets = [
        relation.target_id
        for relation in relations
        if relation.source_id == reservoir_id and relation.relation_type is RelationType.DISCHARGES_TO
    ]
    if len(targets) != 1:
        raise ValueError(f"reservoir {reservoir_id} must have exactly one DISCHARGES_TO relation")
    return targets[0]


def _routing_parameters(repo: HydroRepository, object_id: str, *, dt_seconds: float) -> MuskingumParameters:
    reach = repo.get_object(object_id)
    if reach is None:
        raise ValueError(f"routing reach not found: {object_id}")

    k_minutes = reach.properties.get("routing_k_minutes")
    x = reach.properties.get("routing_x")
    if k_minutes is None or x is None:
        raise ValueError(f"routing reach {object_id} requires routing_k_minutes and routing_x")

    try:
        return MuskingumParameters(
            k_seconds=float(k_minutes) * 60.0,
            x=float(x),
            dt_seconds=dt_seconds,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"routing reach {object_id} has invalid routing_k_minutes or routing_x") from exc


def run_release_scenario(repo: HydroRepository, request: ReleaseScenarioRequest) -> ReleaseScenarioResponse:
    reservoir = repo.get_object(request.reservoir_id)
    if reservoir is None:
        raise KeyError(request.reservoir_id)
    storage = float(reservoir.properties.get("initial_storage_m3", 0))
    max_storage = float(reservoir.properties.get("max_storage_m3", max(storage, 1)))
    level = reservoir.properties.get("initial_level_m")
    state = ReservoirState(
        storage_m3=storage,
        max_storage_m3=max_storage,
        level_m=float(level) if level is not None else None,
    )
    relations = repo.list_relations()
    release_reach_id = _release_reach_id(request.reservoir_id, relations)
    downstream = downstream_path(release_reach_id, relations, max_hops=request.max_hops)
    timestamps = list(range(0, request.duration_minutes + request.dt_minutes, request.dt_minutes))
    dt_seconds = request.dt_minutes * 60
    states: list[HydroState] = []

    for timestamp in timestamps:
        if timestamp > 0:
            state = step_reservoir(
                state,
                ReservoirStep(
                    inflow_cms=request.release_cms * 0.6,
                    outflow_cms=request.release_cms,
                    dt_seconds=dt_seconds,
                ),
            )
        states.append(
            HydroState(
                scenario_id="scenario-release",
                object_id=request.reservoir_id,
                timestamp_minutes=timestamp,
                variable="storage",
                value=state.storage_m3,
                unit="m3",
            )
        )
        if state.level_m is not None:
            states.append(
                HydroState(
                    scenario_id="scenario-release",
                    object_id=request.reservoir_id,
                    timestamp_minutes=timestamp,
                    variable="level",
                    value=state.level_m,
                    unit="m",
                )
            )

    # Treat the requested release as a step change from a lower pre-scenario flow.
    # Route each downstream reach sequentially so the demo shows delay/attenuation.
    routed_series = [request.release_cms for _ in timestamps]
    initial_flow = request.release_cms * 0.35

    for item in downstream:
        params = _routing_parameters(repo, item.object_id, dt_seconds=dt_seconds)
        routed_series = route_muskingum(
            routed_series,
            params,
            initial_outflow_cms=initial_flow,
        )
        initial_flow = routed_series[0]
        for timestamp, flow in zip(timestamps, routed_series, strict=True):
            states.append(
                HydroState(
                    scenario_id="scenario-release",
                    object_id=item.object_id,
                    timestamp_minutes=timestamp,
                    variable="flow",
                    value=flow,
                    unit="m3/s",
                )
            )

    return ReleaseScenarioResponse(scenario_id="scenario-release", states=states)
