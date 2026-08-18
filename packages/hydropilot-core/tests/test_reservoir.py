import pytest
from pydantic import ValidationError

from hydropilot_core.reservoir import (
    ReservoirState,
    ReservoirStep,
    StorageLevelCurve,
    StorageLevelPoint,
    step_reservoir,
)


def test_reservoir_mass_balance_does_not_fabricate_level_without_curve():
    state = ReservoirState(storage_m3=1_000_000, max_storage_m3=2_000_000, level_m=100)
    result = step_reservoir(state, ReservoirStep(inflow_cms=100, outflow_cms=50, dt_seconds=3600))

    assert result.storage_m3 == 1_180_000
    assert result.level_m is None


def test_storage_level_curve_interpolates_piecewise_linearly():
    curve = StorageLevelCurve(
        points=[
            StorageLevelPoint(storage_m3=1_000_000, level_m=100),
            StorageLevelPoint(storage_m3=1_200_000, level_m=110),
            StorageLevelPoint(storage_m3=1_500_000, level_m=120),
        ]
    )

    assert curve.level_for_storage(1_000_000) == pytest.approx(100)
    assert curve.level_for_storage(1_100_000) == pytest.approx(105)
    assert curve.level_for_storage(1_350_000) == pytest.approx(115)
    assert curve.level_for_storage(1_500_000) == pytest.approx(120)


def test_reservoir_step_uses_storage_level_curve_for_resulting_storage():
    curve = StorageLevelCurve(
        points=[
            StorageLevelPoint(storage_m3=1_000_000, level_m=100),
            StorageLevelPoint(storage_m3=1_200_000, level_m=110),
        ]
    )
    state = ReservoirState(storage_m3=1_000_000, max_storage_m3=2_000_000, level_m=100)

    result = step_reservoir(
        state,
        ReservoirStep(inflow_cms=100, outflow_cms=50, dt_seconds=3600),
        storage_level_curve=curve,
    )

    assert result.storage_m3 == 1_180_000
    assert result.level_m == pytest.approx(109)


@pytest.mark.parametrize(
    "points",
    [
        [StorageLevelPoint(storage_m3=1_000_000, level_m=100)],
        [
            StorageLevelPoint(storage_m3=1_000_000, level_m=100),
            StorageLevelPoint(storage_m3=1_000_000, level_m=110),
        ],
        [
            StorageLevelPoint(storage_m3=1_200_000, level_m=100),
            StorageLevelPoint(storage_m3=1_000_000, level_m=110),
        ],
        [
            StorageLevelPoint(storage_m3=1_000_000, level_m=110),
            StorageLevelPoint(storage_m3=1_200_000, level_m=100),
        ],
    ],
)
def test_storage_level_curve_rejects_unusable_points(points):
    with pytest.raises(ValidationError):
        StorageLevelCurve(points=points)


def test_storage_level_curve_rejects_extrapolation():
    curve = StorageLevelCurve(
        points=[
            StorageLevelPoint(storage_m3=1_000_000, level_m=100),
            StorageLevelPoint(storage_m3=1_200_000, level_m=110),
        ]
    )

    with pytest.raises(ValueError, match="outside storage-level curve domain"):
        curve.level_for_storage(900_000)
    with pytest.raises(ValueError, match="outside storage-level curve domain"):
        curve.level_for_storage(1_300_000)


def test_reservoir_preserves_known_level_when_storage_does_not_change():
    state = ReservoirState(storage_m3=1_000_000, max_storage_m3=2_000_000, level_m=100)
    result = step_reservoir(state, ReservoirStep(inflow_cms=50, outflow_cms=50, dt_seconds=3600))

    assert result.storage_m3 == 1_000_000
    assert result.level_m == 100


def test_reservoir_storage_never_negative():
    state = ReservoirState(storage_m3=10, max_storage_m3=100)
    result = step_reservoir(state, ReservoirStep(inflow_cms=0, outflow_cms=1, dt_seconds=3600))
    assert result.storage_m3 == 0


def test_reservoir_rejects_invalid_flow_or_timestep():
    with pytest.raises(ValueError):
        ReservoirStep(inflow_cms=-1, outflow_cms=0, dt_seconds=60)
    with pytest.raises(ValueError):
        ReservoirStep(inflow_cms=0, outflow_cms=0, dt_seconds=0)
