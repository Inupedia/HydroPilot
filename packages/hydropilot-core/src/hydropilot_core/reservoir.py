from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class StorageLevelPoint(BaseModel):
    storage_m3: float = Field(ge=0)
    level_m: float


class StorageLevelCurve(BaseModel):
    points: list[StorageLevelPoint] = Field(min_length=2)

    @model_validator(mode="after")
    def points_must_increase(self) -> "StorageLevelCurve":
        for current, following in zip(self.points, self.points[1:]):
            if current.storage_m3 >= following.storage_m3:
                raise ValueError("storage values must be strictly increasing")
            if current.level_m >= following.level_m:
                raise ValueError("level values must be strictly increasing")
        return self

    def level_for_storage(self, storage_m3: float) -> float:
        if storage_m3 < self.points[0].storage_m3 or storage_m3 > self.points[-1].storage_m3:
            raise ValueError("storage outside storage-level curve domain")

        for current, following in zip(self.points, self.points[1:]):
            if storage_m3 <= following.storage_m3:
                fraction = (storage_m3 - current.storage_m3) / (following.storage_m3 - current.storage_m3)
                return current.level_m + fraction * (following.level_m - current.level_m)

        return self.points[-1].level_m


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


def step_reservoir(
    state: ReservoirState,
    step: ReservoirStep,
    *,
    storage_level_curve: StorageLevelCurve | None = None,
) -> ReservoirState:
    delta = (step.inflow_cms - step.outflow_cms) * step.dt_seconds
    next_storage = min(max(state.storage_m3 + delta, 0.0), state.max_storage_m3)

    if storage_level_curve is not None:
        level = storage_level_curve.level_for_storage(next_storage)
    elif next_storage == state.storage_m3:
        level = state.level_m
    else:
        level = None

    return ReservoirState(storage_m3=next_storage, max_storage_m3=state.max_storage_m3, level_m=level)
