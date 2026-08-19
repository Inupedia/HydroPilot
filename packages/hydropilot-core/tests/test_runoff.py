import pytest

from hydropilot_core.runoff import (
    LinearReservoirParameters,
    LinearReservoirState,
    rainfall_input_cms,
    step_linear_reservoir,
    total_flow_cms,
)


def params(**overrides):
    values = {
        "catchment_area_km2": 100.0,
        "runoff_coefficient": 0.5,
        "response_time_hours": 3.0,
        "baseflow_cms": 5.0,
    }
    values.update(overrides)
    return LinearReservoirParameters(**values)


def test_rainfall_input_converts_depth_and_area_to_discharge():
    flow = rainfall_input_cms(10.0, dt_minutes=60, params=params())
    assert flow == pytest.approx(138.8888889)


def test_dry_interval_recedes_toward_baseflow():
    model = params()
    state = LinearReservoirState(quickflow_cms=20.0)
    next_state = step_linear_reservoir(state, 0.0, dt_minutes=60, params=model)

    assert next_state.quickflow_cms < state.quickflow_cms
    assert total_flow_cms(next_state, model) > model.baseflow_cms


def test_rainfall_pulse_increases_quickflow():
    model = params()
    state = LinearReservoirState(quickflow_cms=20.0)
    next_state = step_linear_reservoir(state, 20.0, dt_minutes=60, params=model)

    assert next_state.quickflow_cms > state.quickflow_cms
    assert total_flow_cms(next_state, model) > 25.0


def test_larger_catchment_produces_larger_rainfall_response():
    state = LinearReservoirState(quickflow_cms=10.0)
    small = step_linear_reservoir(state, 15.0, dt_minutes=60, params=params(catchment_area_km2=50.0))
    large = step_linear_reservoir(state, 15.0, dt_minutes=60, params=params(catchment_area_km2=200.0))

    assert large.quickflow_cms > small.quickflow_cms


def test_negative_rainfall_is_rejected():
    with pytest.raises(ValueError, match="cannot be negative"):
        rainfall_input_cms(-1.0, dt_minutes=60, params=params())
