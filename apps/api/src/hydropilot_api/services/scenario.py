from __future__ import annotations

from pydantic import BaseModel, Field, model_validator
from hydropilot_core.reservoir import ReservoirState, ReservoirStep, step_reservoir
from hydropilot_core.routing import MuskingumParameters, route_muskingum
from hydropilot_api.domain import HydroRelation, HydroState, RelationType
from hydropilot_api.repositories.protocols import HydroRepository
from hydropilot_api.topology import downstream_path


class HydrographPoint(BaseModel):
    timestamp_minutes: int = Field(ge=0)
    flow_cms: float = Field(ge=0)


class ReleaseScenarioRequest(BaseModel):
    reservoir_id: str = "reservoir-shasta"
    release_cms: float = Field(gt=0)
    duration_minutes: int = Field(default=180, gt=0, le=1440)
    dt_minutes: int = Field(default=30, gt=0, le=240)
    max_hops: int = Field(default=4, ge=1, le=12)
    inflow_hydrograph: list[HydrographPoint] = Field(min_length=2)

    @model_validator(mode="after")
    def inflow_boundary_covers_scenario(self) -> "ReleaseScenarioRequest":
        points = self.inflow_hydrograph
        if points[0].timestamp_minutes != 0:
            raise ValueError("inflow hydrograph must start at minute 0")
        if any(
            current.timestamp_minutes >= following.timestamp_minutes
            for current, following in zip(points, points[1:])
        ):
            raise ValueError("inflow hydrograph timestamps must be strictly increasing")
        if points[-1].timestamp_minutes < self.duration_minutes:
            raise ValueError("inflow hydrograph must cover the scenario duration")
        return self


class ReleaseScenarioResponse(BaseModel):
    scenario_id: str
    states: list[HydroState]


def _sample_hydrograph(points: list[HydrographPoint], timestamp_minutes: int) -> float:
    if timestamp_minutes == points[0].timestamp_minutes:
        return points[0].flow_cms

    for current, following in zip(points, points[1:]):
        if timestamp_minutes <= following.timestamp_minutes:
            span = following.timestamp_minutes - current.timestamp_minutes
            fraction = (timestamp_minutes - current.timestamp_minutes) / span
            return current.flow_cms + fraction * (following.flow_cms - current.flow_cms)

    raise ValueError("timestamp outside inflow hydrograph domain")


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
    if timestamps[-1] > request.duration_minutes:
        timestamps[-1] = request.duration_minutes
    timestamps = list(dict.fromkeys(timestamps))
    dt_seconds_default = request.dt_minutes * 60
    sampled_inflow = [_sample_hydrograph(request.inflow_hydrograph, timestamp) for timestamp in timestamps]
    states: list[HydroState] = []

    for idx, timestamp in enumerate(timestamps):
        if idx > 0:
            interval_seconds = (timestamp - timestamps[idx - 1]) * 60
            interval_inflow = (sampled_inflow[idx - 1] + sampled_inflow[idx]) / 2.0
            state = step_reservoir(
                state,
                ReservoirStep(
                    inflow_cms=interval_inflow,
                    outflow_cms=request.release_cms,
                    dt_seconds=interval_seconds,
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
        states.append(
            HydroState(
                scenario_id="scenario-release",
                object_id=request.reservoir_id,
                timestamp_minutes=timestamp,
                variable="inflow",
                value=sampled_inflow[idx],
                unit="m3/s",
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
        params = _routing_parameters(repo, item.object_id, dt_seconds=dt_seconds_default)
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
