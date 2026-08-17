import pytest
from hydropilot_core.reservoir import ReservoirState, ReservoirStep, step_reservoir


def test_reservoir_mass_balance_reference_case():
    state = ReservoirState(storage_m3=1_000_000, max_storage_m3=2_000_000, level_m=100)
    result = step_reservoir(state, ReservoirStep(inflow_cms=100, outflow_cms=50, dt_seconds=3600))
    assert result.storage_m3 == 1_180_000
    assert result.level_m == pytest.approx(104.5)


def test_reservoir_storage_never_negative():
    state = ReservoirState(storage_m3=10, max_storage_m3=100)
    result = step_reservoir(state, ReservoirStep(inflow_cms=0, outflow_cms=1, dt_seconds=3600))
    assert result.storage_m3 == 0


def test_reservoir_rejects_invalid_flow_or_timestep():
    with pytest.raises(ValueError):
        ReservoirStep(inflow_cms=-1, outflow_cms=0, dt_seconds=60)
    with pytest.raises(ValueError):
        ReservoirStep(inflow_cms=0, outflow_cms=0, dt_seconds=0)
