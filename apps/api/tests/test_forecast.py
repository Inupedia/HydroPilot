import pytest
from pydantic import ValidationError

from hydropilot_api.services.forecast import (
    FlowForecastRequest,
    FlowObservation,
    ForecastModel,
    ForecastTrend,
    run_flow_forecast,
)


def observation(timestamp_minutes: int, flow_cms: float) -> FlowObservation:
    return FlowObservation(timestamp_minutes=timestamp_minutes, flow_cms=flow_cms)


def test_damped_trend_forecast_projects_future_from_history_only():
    result = run_flow_forecast(
        FlowForecastRequest(
            object_id="reservoir-alpha",
            history=[
                observation(-60, 100),
                observation(-30, 120),
                observation(0, 140),
            ],
            horizon_minutes=90,
            dt_minutes=30,
            damping=0.5,
        )
    )

    assert [point.timestamp_minutes for point in result.forecast] == [30, 60, 90]
    assert [point.flow_cms for point in result.forecast] == pytest.approx([160, 170, 175])
    assert result.summary.current_flow_cms == pytest.approx(140)
    assert result.summary.peak_flow_cms == pytest.approx(175)
    assert result.summary.peak_timestamp_minutes == 90
    assert result.summary.peak_change_pct == pytest.approx(25)
    assert result.summary.trend is ForecastTrend.RISING


def test_persistence_forecast_keeps_current_flow_flat():
    result = run_flow_forecast(
        FlowForecastRequest(
            object_id="reach-alpha",
            history=[
                observation(-30, 90),
                observation(0, 120),
            ],
            horizon_minutes=60,
            dt_minutes=30,
            model=ForecastModel.PERSISTENCE,
        )
    )

    assert [point.flow_cms for point in result.forecast] == pytest.approx([120, 120])
    assert result.summary.peak_flow_cms == pytest.approx(120)
    assert result.summary.peak_timestamp_minutes == 30
    assert result.summary.peak_change_pct == pytest.approx(0)
    assert result.summary.trend is ForecastTrend.STEADY


def test_falling_forecast_never_produces_negative_flow():
    result = run_flow_forecast(
        FlowForecastRequest(
            object_id="reach-alpha",
            history=[
                observation(-30, 20),
                observation(0, 5),
            ],
            horizon_minutes=90,
            dt_minutes=30,
            damping=1.0,
        )
    )

    assert [point.flow_cms for point in result.forecast] == pytest.approx([0, 0, 0])
    assert result.summary.trend is ForecastTrend.FALLING


def test_forecast_request_requires_now_anchored_strict_history_and_time_grid():
    with pytest.raises(ValidationError, match="end at minute 0"):
        FlowForecastRequest(
            object_id="reach-alpha",
            history=[observation(-60, 10), observation(-30, 20)],
        )

    with pytest.raises(ValidationError, match="strictly increasing"):
        FlowForecastRequest(
            object_id="reach-alpha",
            history=[observation(-30, 10), observation(-30, 20), observation(0, 30)],
        )

    with pytest.raises(ValidationError, match="must be divisible"):
        FlowForecastRequest(
            object_id="reach-alpha",
            history=[observation(-30, 10), observation(0, 20)],
            horizon_minutes=50,
            dt_minutes=30,
        )
