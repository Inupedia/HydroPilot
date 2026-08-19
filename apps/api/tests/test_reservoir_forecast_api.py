from fastapi.testclient import TestClient

from hydropilot_api.main import app


client = TestClient(app)


def payload(reservoir_id="reservoir-shasta"):
    return {
        "reservoir_id": reservoir_id,
        "rainfall": [
            {"timestamp_minutes": 30, "precipitation_mm": 0},
            {"timestamp_minutes": 60, "precipitation_mm": 3},
            {"timestamp_minutes": 90, "precipitation_mm": 8},
            {"timestamp_minutes": 120, "precipitation_mm": 14},
            {"timestamp_minutes": 150, "precipitation_mm": 7},
            {"timestamp_minutes": 180, "precipitation_mm": 2},
        ],
        "dt_minutes": 30,
        "initial_inflow_cms": 1000,
        "release_cms": 1500,
        "catchment_area_km2": 8000,
        "runoff_coefficient": 0.18,
        "response_time_hours": 8,
        "baseflow_cms": 570,
        "max_hops": 6,
    }


def test_reservoir_forecast_api_returns_runoff_and_storage_projection():
    response = client.post("/api/forecasts/reservoir", json=payload())

    assert response.status_code == 200
    body = response.json()
    assert body["reservoir_id"] == "reservoir-shasta"
    assert body["model"] == "rainfall_runoff_plus_reservoir_balance"
    assert body["runoff"]["summary"]["total_rainfall_mm"] == 34
    assert body["summary"]["peak_inflow_cms"] > 1000
    assert body["summary"]["current_storage_m3"] == 4_100_000_000
    assert body["summary"]["final_storage_m3"] != body["summary"]["current_storage_m3"]
    assert body["summary"]["final_level_m"] is None


def test_reservoir_forecast_api_returns_404_for_unknown_reservoir():
    response = client.post("/api/forecasts/reservoir", json=payload("missing-reservoir"))

    assert response.status_code == 404
