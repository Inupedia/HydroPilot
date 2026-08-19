from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class ForecastModel(str, Enum):
    PERSISTENCE = "persistence"
    DAMPED_TREND = "damped_trend"


class ForecastTrend(str, Enum):
    RISING = "rising"
    FALLING = "falling"
    STEADY = "steady"


class FlowObservation(BaseModel):
    timestamp_minutes: int = Field(le=0)
    flow_cms: float = Field(ge=0)


class FlowForecastRequest(BaseModel):
    object_id: str
    history: list[FlowObservation] = Field(min_length=2)
    horizon_minutes: int = Field(default=360, gt=0, le=4320)
    dt_minutes: int = Field(default=30, gt=0, le=360)
    model: ForecastModel = ForecastModel.DAMPED_TREND
    trend_window_points: int = Field(default=4, ge=2, le=24)
    damping: float = Field(default=0.85, ge=0, le=1)

    @model_validator(mode="after")
    def validate_history_and_grid(self) -> "FlowForecastRequest":
        if self.horizon_minutes % self.dt_minutes != 0:
            raise ValueError("horizon_minutes must be divisible by dt_minutes")
        if self.history[-1].timestamp_minutes != 0:
            raise ValueError("history must end at minute 0 (NOW)")
        if any(
            current.timestamp_minutes >= following.timestamp_minutes
            for current, following in zip(self.history, self.history[1:])
        ):
            raise ValueError("history timestamps must be strictly increasing")
        return self


class FlowForecastPoint(BaseModel):
    timestamp_minutes: int = Field(gt=0)
    flow_cms: float = Field(ge=0)


class FlowForecastSummary(BaseModel):
    current_flow_cms: float = Field(ge=0)
    peak_flow_cms: float = Field(ge=0)
    peak_timestamp_minutes: int = Field(gt=0)
    peak_change_pct: float | None = None
    trend: ForecastTrend


class FlowForecastResponse(BaseModel):
    object_id: str
    model: ForecastModel
    horizon_minutes: int
    dt_minutes: int
    forecast: list[FlowForecastPoint]
    summary: FlowForecastSummary


def _trend_slope_cms_per_minute(request: FlowForecastRequest) -> float:
    if request.model is ForecastModel.PERSISTENCE:
        return 0.0

    window = request.history[-min(request.trend_window_points, len(request.history)) :]
    first = window[0]
    last = window[-1]
    elapsed_minutes = last.timestamp_minutes - first.timestamp_minutes
    if elapsed_minutes <= 0:
        raise ValueError("forecast trend window must span a positive duration")
    return (last.flow_cms - first.flow_cms) / elapsed_minutes


def run_flow_forecast(request: FlowForecastRequest) -> FlowForecastResponse:
    current_flow = request.history[-1].flow_cms
    slope = _trend_slope_cms_per_minute(request)
    value = current_flow
    forecast: list[FlowForecastPoint] = []

    steps = request.horizon_minutes // request.dt_minutes
    for step in range(1, steps + 1):
        if request.model is ForecastModel.DAMPED_TREND:
            increment = slope * request.dt_minutes * (request.damping ** (step - 1))
            value = max(value + increment, 0.0)
        else:
            value = current_flow

        forecast.append(
            FlowForecastPoint(
                timestamp_minutes=step * request.dt_minutes,
                flow_cms=value,
            )
        )

    peak = max(forecast, key=lambda point: point.flow_cms)
    final_flow = forecast[-1].flow_cms
    tolerance = max(1e-6, current_flow * 1e-6)
    if final_flow > current_flow + tolerance:
        trend = ForecastTrend.RISING
    elif final_flow < current_flow - tolerance:
        trend = ForecastTrend.FALLING
    else:
        trend = ForecastTrend.STEADY

    peak_change_pct = None
    if current_flow > 0:
        peak_change_pct = ((peak.flow_cms - current_flow) / current_flow) * 100.0

    return FlowForecastResponse(
        object_id=request.object_id,
        model=request.model,
        horizon_minutes=request.horizon_minutes,
        dt_minutes=request.dt_minutes,
        forecast=forecast,
        summary=FlowForecastSummary(
            current_flow_cms=current_flow,
            peak_flow_cms=peak.flow_cms,
            peak_timestamp_minutes=peak.timestamp_minutes,
            peak_change_pct=peak_change_pct,
            trend=trend,
        ),
    )
