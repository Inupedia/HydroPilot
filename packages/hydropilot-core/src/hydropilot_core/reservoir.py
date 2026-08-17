from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ReservoirState(BaseModel):
    storage_m3: float = Field(ge=0)
    max_storage_m3: float = Field(gt=0)
    level_m: float | None = None

    @model_validator(mode="after")
    def storage_cannot_exceed_capacity(self) -> "ReservoirState":
        if self.storage_m3 > self.max_storage_m3:
            raise ValueError("storage_m3 cannot exceed max_storage_m3")
        return self


class ReservoirStep(BaseModel):
    inflow_cms: float = Field(ge=0)
    outflow_cms: float = Field(ge=0)
    dt_seconds: float = Field(gt=0)


def step_reservoir(state: ReservoirState, step: ReservoirStep) -> ReservoirState:
    delta = (step.inflow_cms - step.outflow_cms) * step.dt_seconds
    next_storage = min(max(state.storage_m3 + delta, 0.0), state.max_storage_m3)
    level = state.level_m
    if level is not None and state.max_storage_m3 > 0:
        storage_ratio_delta = (next_storage - state.storage_m3) / state.max_storage_m3
        level = level + storage_ratio_delta * 50.0
    return ReservoirState(storage_m3=next_storage, max_storage_m3=state.max_storage_m3, level_m=level)
