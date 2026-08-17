from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class MuskingumParameters(BaseModel):
    k_seconds: float = Field(gt=0)
    x: float = Field(ge=0, le=0.5)
    dt_seconds: float = Field(gt=0)

    @model_validator(mode="after")
    def stable_coefficients(self) -> "MuskingumParameters":
        denominator = 2 * self.k_seconds * (1 - self.x) + self.dt_seconds
        c0 = (self.dt_seconds - 2 * self.k_seconds * self.x) / denominator
        c1 = (self.dt_seconds + 2 * self.k_seconds * self.x) / denominator
        c2 = (2 * self.k_seconds * (1 - self.x) - self.dt_seconds) / denominator
        if min(c0, c1, c2) < -1e-9:
            raise ValueError("unstable Muskingum parameter combination")
        return self


def coefficients(params: MuskingumParameters) -> tuple[float, float, float]:
    denominator = 2 * params.k_seconds * (1 - params.x) + params.dt_seconds
    c0 = (params.dt_seconds - 2 * params.k_seconds * params.x) / denominator
    c1 = (params.dt_seconds + 2 * params.k_seconds * params.x) / denominator
    c2 = (2 * params.k_seconds * (1 - params.x) - params.dt_seconds) / denominator
    return c0, c1, c2


def route_muskingum(inflow_cms: list[float], params: MuskingumParameters, initial_outflow_cms: float | None = None) -> list[float]:
    if not inflow_cms:
        return []
    if any(flow < 0 for flow in inflow_cms):
        raise ValueError("inflow hydrograph cannot contain negative values")
    c0, c1, c2 = coefficients(params)
    outflow = [inflow_cms[0] if initial_outflow_cms is None else initial_outflow_cms]
    for idx in range(1, len(inflow_cms)):
        routed = c0 * inflow_cms[idx] + c1 * inflow_cms[idx - 1] + c2 * outflow[idx - 1]
        outflow.append(max(routed, 0.0))
    return outflow
