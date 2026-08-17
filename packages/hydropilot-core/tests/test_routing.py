import pytest
from hydropilot_core.routing import MuskingumParameters, route_muskingum


def test_muskingum_routes_reference_hydrograph():
    inflow = [10, 20, 60, 120, 80, 40, 20]
    routed = route_muskingum(inflow, MuskingumParameters(k_seconds=3600, x=0.2, dt_seconds=1800))
    assert len(routed) == len(inflow)
    assert max(routed) < max(inflow)
    assert routed.index(max(routed)) >= inflow.index(max(inflow))
    assert routed[-1] == pytest.approx(57.999, rel=1e-3)


def test_muskingum_rejects_invalid_parameters():
    with pytest.raises(ValueError):
        MuskingumParameters(k_seconds=3600, x=0.49, dt_seconds=60)


def test_muskingum_rejects_negative_inflow():
    with pytest.raises(ValueError):
        route_muskingum([1, -1], MuskingumParameters(k_seconds=3600, x=0.2, dt_seconds=1800))
