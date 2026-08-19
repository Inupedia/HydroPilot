from __future__ import annotations

import math
from collections import defaultdict

from pydantic import BaseModel, Field, model_validator
from hydropilot_core.reservoir import (
    ReservoirState,
    ReservoirStep,
    StorageLevelCurve,
    StorageLevelPoint,
    step_reservoir,
)
from hydropilot_core.routing import MuskingumParameters, route_muskingum
from hydropilot_api.domain import (
    ConstraintType,
    CurveType,
    HydroConstraint,
    HydroRelation,
    HydroState,
    RelationType,
)
from hydropilot_api.repositories.protocols import HydroRepository


class HydrographPoint(BaseModel):
    timestamp_minutes: int = Field(ge=0)
    flow_cms: float = Field(ge=0)


def _validate_hydrograph_boundary(
    name: str,
    points: list[HydrographPoint],
    *,
    duration_minutes: int,
) -> None:
    if points[0].timestamp_minutes != 0:
        raise ValueError(f"{name} hydrograph must start at minute 0")
    if any(
        current.timestamp_minutes >= following.timestamp_minutes
        for current, following in zip(points, points[1:])
    ):
        raise ValueError(f"{name} hydrograph timestamps must be strictly increasing")
    if points[-1].timestamp_minutes < duration_minutes:
        raise ValueError(f"{name} hydrograph must cover the scenario duration")


class ReleaseScenarioRequest(BaseModel):
    reservoir_id: str = "reservoir-shasta"
    duration_minutes: int = Field(default=180, gt=0, le=1440)
    dt_minutes: int = Field(default=30, gt=0, le=240)
    max_hops: int = Field(default=4, ge=1, le=12)
    inflow_hydrograph: list[HydrographPoint] = Field(min_length=2)
    release_hydrograph: list[HydrographPoint] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_time_grid_and_boundaries(self) -> "ReleaseScenarioRequest":
        if self.duration_minutes % self.dt_minutes != 0:
            raise ValueError("duration_minutes must be divisible by dt_minutes")

        _validate_hydrograph_boundary(
            "inflow",
            self.inflow_hydrograph,
            duration_minutes=self.duration_minutes,
        )
        _validate_hydrograph_boundary(
            "release",
            self.release_hydrograph,
            duration_minutes=self.duration_minutes,
        )
        return self


class ConstraintViolation(BaseModel):
    constraint_id: str
    object_id: str
    variable: str
    timestamp_minutes: int
    value: float
    unit: str
    constraint_type: ConstraintType
    min_value: float | None = None
    max_value: float | None = None
    source: str


class UnevaluatedConstraint(BaseModel):
    constraint_id: str
    object_id: str
    variable: str
    reason: str


class ReleaseScenarioResponse(BaseModel):
    scenario_id: str
    states: list[HydroState]
    violations: list[ConstraintViolation] = Field(default_factory=list)
    unevaluated_constraints: list[UnevaluatedConstraint] = Field(default_factory=list)


def _sample_hydrograph(points: list[HydrographPoint], timestamp_minutes: int) -> float:
    if timestamp_minutes == points[0].timestamp_minutes:
        return points[0].flow_cms

    for current, following in zip(points, points[1:]):
        if timestamp_minutes <= following.timestamp_minutes:
            span = following.timestamp_minutes - current.timestamp_minutes
            fraction = (timestamp_minutes - current.timestamp_minutes) / span
            return current.flow_cms + fraction * (following.flow_cms - current.flow_cms)

    raise ValueError("timestamp outside hydrograph domain")


def _release_reach_id(reservoir_id: str, relations: list[HydroRelation]) -> str:
    targets = [
        relation.target_id
        for relation in relations
        if relation.source_id == reservoir_id and relation.relation_type is RelationType.DISCHARGES_TO
    ]
    if len(targets) != 1:
        raise ValueError(f"reservoir {reservoir_id} must have exactly one DISCHARGES_TO relation")
    return targets[0]


def _routing_chain_ids(start_id: str, relations: list[HydroRelation], *, max_hops: int) -> list[str]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for relation in relations:
        if relation.relation_type is RelationType.FLOWS_TO:
            adjacency[relation.source_id].add(relation.target_id)

    chain = [start_id]
    seen = {start_id}
    current = start_id

    for _ in range(max_hops):
        targets = sorted(adjacency.get(current, set()))
        if len(targets) > 1:
            raise ValueError(f"branching FLOWS_TO topology is unsupported at {current}")
        if not targets:
            break

        target = targets[0]
        if target in seen:
            raise ValueError(f"cyclic FLOWS_TO topology is unsupported at {target}")

        chain.append(target)
        seen.add(target)
        current = target

    return chain


def _storage_level_curve(repo: HydroRepository, reservoir_id: str) -> StorageLevelCurve | None:
    curves = repo.list_curves(object_id=reservoir_id, curve_type=CurveType.LEVEL_STORAGE)
    if len(curves) > 1:
        raise ValueError(f"reservoir {reservoir_id} must have at most one level-storage curve")
    if not curves:
        return None

    curve = curves[0]
    if curve.x_unit != "m" or curve.y_unit != "m3":
        raise ValueError("level-storage curve requires x_unit=m and y_unit=m3")

    return StorageLevelCurve(
        points=[
            StorageLevelPoint(storage_m3=point.y, level_m=point.x)
            for point in curve.points
        ]
    )


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


def _constraint_is_violated(constraint: HydroConstraint, value: float) -> bool:
    if constraint.constraint_type is ConstraintType.MINIMUM:
        return value < float(constraint.min_value)
    if constraint.constraint_type is ConstraintType.MAXIMUM:
        return value > float(constraint.max_value)
    if constraint.constraint_type is ConstraintType.RANGE:
        return value < float(constraint.min_value) or value > float(constraint.max_value)
    return False


def _evaluate_ramp_rate_constraint(
    constraint: HydroConstraint,
    matching_states: list[HydroState],
) -> tuple[list[ConstraintViolation], UnevaluatedConstraint | None]:
    if len(matching_states) < 2:
        return [], UnevaluatedConstraint(
            constraint_id=constraint.id,
            object_id=constraint.object_id,
            variable=constraint.variable,
            reason="ramp-rate constraint requires at least two matching states",
        )

    state_units = {state.unit for state in matching_states}
    if len(state_units) != 1:
        raise ValueError(f"scenario states have inconsistent units for {constraint.id}")

    state_unit = next(iter(state_units))
    expected_unit = f"{state_unit}/h"
    if constraint.unit != expected_unit:
        return [], UnevaluatedConstraint(
            constraint_id=constraint.id,
            object_id=constraint.object_id,
            variable=constraint.variable,
            reason=f"ramp-rate unit {constraint.unit} is unsupported; expected {expected_unit}",
        )

    violations: list[ConstraintViolation] = []
    for current, following in zip(matching_states, matching_states[1:]):
        elapsed_minutes = following.timestamp_minutes - current.timestamp_minutes
        if elapsed_minutes <= 0:
            return [], UnevaluatedConstraint(
                constraint_id=constraint.id,
                object_id=constraint.object_id,
                variable=constraint.variable,
                reason="ramp-rate constraint requires strictly increasing state timestamps",
            )
        elapsed_hours = elapsed_minutes / 60.0
        rate = abs(following.value - current.value) / elapsed_hours
        if rate > float(constraint.max_value):
            violations.append(
                ConstraintViolation(
                    constraint_id=constraint.id,
                    object_id=constraint.object_id,
                    variable=constraint.variable,
                    timestamp_minutes=following.timestamp_minutes,
                    value=rate,
                    unit=constraint.unit,
                    constraint_type=constraint.constraint_type,
                    min_value=constraint.min_value,
                    max_value=constraint.max_value,
                    source=constraint.source,
                )
            )

    return violations, None


def _evaluate_constraints(
    repo: HydroRepository,
    states: list[HydroState],
) -> tuple[list[ConstraintViolation], list[UnevaluatedConstraint]]:
    by_object_variable: dict[tuple[str, str], list[HydroState]] = defaultdict(list)
    for state in states:
        by_object_variable[(state.object_id, state.variable)].append(state)

    violations: list[ConstraintViolation] = []
    unevaluated: list[UnevaluatedConstraint] = []

    for object_id in sorted({state.object_id for state in states}):
        for constraint in repo.list_constraints(object_id=object_id):
            if constraint.active_when:
                unevaluated.append(
                    UnevaluatedConstraint(
                        constraint_id=constraint.id,
                        object_id=constraint.object_id,
                        variable=constraint.variable,
                        reason="conditional constraints are not evaluated",
                    )
                )
                continue

            matching_states = sorted(
                by_object_variable.get((constraint.object_id, constraint.variable), []),
                key=lambda state: state.timestamp_minutes,
            )
            if not matching_states:
                unevaluated.append(
                    UnevaluatedConstraint(
                        constraint_id=constraint.id,
                        object_id=constraint.object_id,
                        variable=constraint.variable,
                        reason="scenario has no matching state variable",
                    )
                )
                continue

            if constraint.constraint_type is ConstraintType.RAMP_RATE:
                ramp_violations, ramp_unevaluated = _evaluate_ramp_rate_constraint(
                    constraint,
                    matching_states,
                )
                violations.extend(ramp_violations)
                if ramp_unevaluated is not None:
                    unevaluated.append(ramp_unevaluated)
                continue

            for state in matching_states:
                if state.unit != constraint.unit:
                    raise ValueError(
                        f"constraint unit {constraint.unit} does not match scenario unit {state.unit} "
                        f"for {constraint.id}"
                    )

            for state in matching_states:
                if _constraint_is_violated(constraint, state.value):
                    violations.append(
                        ConstraintViolation(
                            constraint_id=constraint.id,
                            object_id=constraint.object_id,
                            variable=constraint.variable,
                            timestamp_minutes=state.timestamp_minutes,
                            value=state.value,
                            unit=state.unit,
                            constraint_type=constraint.constraint_type,
                            min_value=constraint.min_value,
                            max_value=constraint.max_value,
                            source=constraint.source,
                        )
                    )

    return violations, unevaluated


def _reservoir_storage_inputs(reservoir_id: str, properties: dict) -> tuple[float, float]:
    initial_storage = properties.get("initial_storage_m3")
    max_storage = properties.get("max_storage_m3")
    if initial_storage is None or max_storage is None:
        raise ValueError(
            f"reservoir {reservoir_id} requires initial_storage_m3 and max_storage_m3"
        )
    if isinstance(initial_storage, bool) or isinstance(max_storage, bool):
        raise ValueError(
            f"reservoir {reservoir_id} has invalid initial_storage_m3 or max_storage_m3"
        )
    try:
        storage = float(initial_storage)
        capacity = float(max_storage)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"reservoir {reservoir_id} has invalid initial_storage_m3 or max_storage_m3"
        ) from exc
    if not math.isfinite(storage) or not math.isfinite(capacity):
        raise ValueError(
            f"reservoir {reservoir_id} has invalid initial_storage_m3 or max_storage_m3"
        )
    return storage, capacity


def run_release_scenario(repo: HydroRepository, request: ReleaseScenarioRequest) -> ReleaseScenarioResponse:
    reservoir = repo.get_object(request.reservoir_id)
    if reservoir is None:
        raise KeyError(request.reservoir_id)
    storage, max_storage = _reservoir_storage_inputs(
        request.reservoir_id,
        reservoir.properties,
    )
    storage_level_curve = _storage_level_curve(repo, request.reservoir_id)
    if storage_level_curve is not None:
        level = storage_level_curve.level_for_storage(storage)
    else:
        initial_level = reservoir.properties.get("initial_level_m")
        level = float(initial_level) if initial_level is not None else None
    state = ReservoirState(
        storage_m3=storage,
        max_storage_m3=max_storage,
        level_m=level,
    )
    relations = repo.list_relations()
    release_reach_id = _release_reach_id(request.reservoir_id, relations)
    routed_object_ids = _routing_chain_ids(release_reach_id, relations, max_hops=request.max_hops)
    timestamps = list(range(0, request.duration_minutes + request.dt_minutes, request.dt_minutes))
    dt_seconds = request.dt_minutes * 60
    sampled_inflow = [_sample_hydrograph(request.inflow_hydrograph, timestamp) for timestamp in timestamps]
    sampled_release = [_sample_hydrograph(request.release_hydrograph, timestamp) for timestamp in timestamps]
    states: list[HydroState] = []

    for idx, timestamp in enumerate(timestamps):
        if idx > 0:
            interval_inflow = (sampled_inflow[idx - 1] + sampled_inflow[idx]) / 2.0
            interval_release = (sampled_release[idx - 1] + sampled_release[idx]) / 2.0
            state = step_reservoir(
                state,
                ReservoirStep(
                    inflow_cms=interval_inflow,
                    outflow_cms=interval_release,
                    dt_seconds=dt_seconds,
                ),
                storage_level_curve=storage_level_curve,
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
        states.append(
            HydroState(
                scenario_id="scenario-release",
                object_id=request.reservoir_id,
                timestamp_minutes=timestamp,
                variable="release",
                value=sampled_release[idx],
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

    routed_series = list(sampled_release)
    for object_id in routed_object_ids:
        params = _routing_parameters(repo, object_id, dt_seconds=dt_seconds)
        routed_series = route_muskingum(
            routed_series,
            params,
            initial_outflow_cms=routed_series[0],
        )
        for timestamp, flow in zip(timestamps, routed_series, strict=True):
            states.append(
                HydroState(
                    scenario_id="scenario-release",
                    object_id=object_id,
                    timestamp_minutes=timestamp,
                    variable="flow",
                    value=flow,
                    unit="m3/s",
                )
            )

    violations, unevaluated_constraints = _evaluate_constraints(repo, states)
    return ReleaseScenarioResponse(
        scenario_id="scenario-release",
        states=states,
        violations=violations,
        unevaluated_constraints=unevaluated_constraints,
    )