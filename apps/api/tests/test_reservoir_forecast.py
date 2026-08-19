from pathlib import Path

import pytest
from pydantic import ValidationError

from hydropilot_api.repositories.fixture import FixtureHydroRepository
from hydropilot_api.services.reservoir_forecast import (
    ReservoirRainfallForecastRequest,
    run_reservoir_rainfall_forecast,
)
from hydropilot_api.services.runoff_forecast import RainfallForecastPoint


FIXTURE_PATH = Path(__file__).resolve().parents[3] / "data" / "demo" / "sacramento_v0_1.json"


def rainfall(values, dt_minutes=30):
    return [
        RainfallForecastPoint(
            timestamp_minutes=(index + 1) * dt_minutes,
            precipitation_mm=value,
        )
        for index, value in enumerate(values)
    ]


def request(values=None, **overrides):
    data = {
        "reservoir_id": "reservoir-shasta",
        "rainfall": rainfall(values or [0, 3, 8, 14, 7, 2]),
        "dt_minutes": 30,
        "initial_inflow_cms": 1000,
        "release_cms": 1500,
        "catchment_area_km2": 8000,
        "runoff_coefficient": 0.18,
        "response_time_hours": 8,
        "baseflow_cms": 570,
        "max_hops": 6,
    }
    data.update(overrides)
    return ReservoirRainfallForecastRequest(**data)


def test_rainfall_runoff_is_used_as_reservoir_inflow_boundary():
    repo = FixtureHydroRepository(FIXTURE_PATH)
    result = run_reservoir_rainfall_forecast(repo, request())

    inflow_states = [
        state
        for state in result.scenario.states
        if state.object_id == "reservoir-shasta" and state.variable == "inflow"
    ]
    assert [state.value for state in inflow_states[1:]] == pytest.approx(
        [point.flow_cms for point in result.runoff.runoff]
    )
    assert result.summary.peak_inflow_cms > result.summary.current_storage_m3 * 0
    assert result.summary.peak_inflow_cms == pytest.approx(result.runoff.summary.peak_flow_cms)
    assert result.summary.peak_inflow_timestamp_minutes == result.runoff.summary.peak_timestamp_minutes


def test_reservoir_storage_changes_but_level_is_not_invented_without_curve():
    repo = FixtureHydroRepository(FIXTURE_PATH)
    result = run_reservoir_rainfall_forecast(repo, request())

    assert result.summary.current_storage_m3 == pytest.approx(4_100_000_000)
    assert result.summary.final_storage_m3 != pytest.approx(result.summary.current_storage_m3)
    assert result.summary.min_storage_m3 <= result.summary.final_storage_m3 <= result.summary.max_storage_m3
    assert result.summary.storage_change_m3 == pytest.approx(
        result.summary.final_storage_m3 - result.summary.current_storage_m3
    )
    assert result.summary.final_level_m is None


def test_fixed_release_remains_backward_compatible_when_response_fraction_is_zero():
    repo = FixtureHydroRepository(FIXTURE_PATH)
    result = run_reservoir_rainfall_forecast(repo, request(release_response_fraction=0))
    release_states = [
        state.value
        for state in result.scenario.states
        if state.object_id == "reservoir-shasta" and state.variable == "release"
    ]

    assert release_states
    assert release_states == pytest.approx([1500] * len(release_states))
    assert result.summary.peak_release_cms == pytest.approx(1500)
    assert result.summary.release_response_fraction == 0


def test_responsive_release_turns_rainfall_forecast_into_dynamic_downstream_wave():
    repo = FixtureHydroRepository(FIXTURE_PATH)
    result = run_reservoir_rainfall_forecast(
        repo,
        request(
            max_hops=20,
            release_response_fraction=0.65,
            max_release_cms=4000,
        ),
    )

    release_states = sorted(
        [
            state
            for state in result.scenario.states
            if state.object_id == "reservoir-shasta" and state.variable == "release"
        ],
        key=lambda state: state.timestamp_minutes,
    )
    first_reach = sorted(
        [state for state in result.scenario.states if state.object_id == "reach-001" and state.variable == "flow"],
        key=lambda state: state.timestamp_minutes,
    )
    control = sorted(
        [state for state in result.scenario.states if state.object_id == "control-sacramento" and state.variable == "flow"],
        key=lambda state: state.timestamp_minutes,
    )

    assert max(state.value for state in release_states) > 1500
    assert max(state.value for state in release_states) <= 4000
    assert len({round(state.value, 6) for state in first_reach}) > 1
    assert len({round(state.value, 6) for state in control}) > 1
    assert result.summary.peak_release_cms == pytest.approx(max(state.value for state in release_states))
    assert result.summary.release_response_fraction == pytest.approx(0.65)


def test_responsive_release_cap_cannot_be_lower_than_baseline_release():
    with pytest.raises(ValidationError, match="max_release_cms"):
        request(release_cms=1500, max_release_cms=1400)


def test_full_network_forecast_reaches_terminal_reach_and_control_point():
    repo = FixtureHydroRepository(FIXTURE_PATH)
    result = run_reservoir_rainfall_forecast(repo, request(max_hops=20))

    terminal = sorted(
        [state for state in result.scenario.states if state.object_id == "reach-020" and state.variable == "flow"],
        key=lambda state: state.timestamp_minutes,
    )
    control = sorted(
        [state for state in result.scenario.states if state.object_id == "control-sacramento" and state.variable == "flow"],
        key=lambda state: state.timestamp_minutes,
    )

    assert terminal
    assert [state.timestamp_minutes for state in control] == [state.timestamp_minutes for state in terminal]
    assert [state.value for state in control] == pytest.approx([state.value for state in terminal])


def test_reservoir_forecast_accepts_up_to_twenty_five_routing_hops():
    assert request(max_hops=20).max_hops == 20
    assert request(max_hops=25).max_hops == 25
    with pytest.raises(ValidationError, match="25"):
        request(max_hops=26)


def test_reservoir_forecast_rejects_horizon_beyond_release_scenario_limit():
    with pytest.raises(ValidationError, match="1440"):
        request(
            values=[1, 1],
            rainfall=[
                RainfallForecastPoint(timestamp_minutes=30, precipitation_mm=1),
                RainfallForecastPoint(timestamp_minutes=1470, precipitation_mm=1),
            ],
        )
