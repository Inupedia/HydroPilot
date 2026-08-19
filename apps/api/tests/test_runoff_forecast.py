import pytest
from pydantic import ValidationError

from hydropilot_api.services.runoff_forecast import (
    RainfallForecastPoint,
    RunoffForecastRequest,
    run_runoff_forecast,
)


def rainfall(values, dt_minutes=60):
    return [
        RainfallForecastPoint(timestamp_minutes=(index + 1) * dt_minutes, precipitation_mm=value)
        for index, value in enumerate(values)
    ]


def request(values, **overrides):
    data = {
        "object_id": "gauge-keswick",
        "rainfall": rainfall(values),
        "dt_minutes": 60,
        "initial_flow_cms": 25.0,
        "catchment_area_km2": 100.0,
        "runoff_coefficient": 0.5,
        "response_time_hours": 3.0,
        "baseflow_cms": 5.0,
    }
    data.update(overrides)
    return RunoffForecastRequest(**data)


def test_dry_forecast_recedes_from_current_flow():
    result = run_runoff_forecast(request([0, 0, 0]))

    assert result.runoff[0].flow_cms < 25.0
    assert result.runoff[-1].flow_cms < result.runoff[0].flow_cms
    assert result.summary.total_rainfall_mm == 0


def test_rainfall_forecast_generates_future_runoff_peak():
    result = run_runoff_forecast(request([0, 10, 20, 5]))

    assert result.horizon_minutes == 240
    assert result.summary.total_rainfall_mm == 35
    assert result.summary.peak_flow_cms > result.summary.current_flow_cms
    assert result.summary.peak_timestamp_minutes in {120, 180, 240}
    assert result.summary.peak_change_pct is not None
    assert len(result.runoff) == 4


def test_request_requires_contiguous_rainfall_grid():
    with pytest.raises(ValidationError, match="contiguous"):
        RunoffForecastRequest(
            object_id="gauge-keswick",
            rainfall=[
                RainfallForecastPoint(timestamp_minutes=60, precipitation_mm=5),
                RainfallForecastPoint(timestamp_minutes=180, precipitation_mm=10),
            ],
            dt_minutes=60,
            initial_flow_cms=20,
            catchment_area_km2=100,
        )


def test_baseflow_cannot_exceed_current_flow():
    with pytest.raises(ValidationError, match="baseflow"):
        request([5, 5], baseflow_cms=30.0)
