from fastapi.testclient import TestClient

from hydropilot_api.main import app


client = TestClient(app)


def payload(object_id="gauge-keswick"):
    return {
        "object_id": object_id,
        "rainfall": [
            {"timestamp_minutes": 60, "precipitation_mm": 0},
            {"timestamp_minutes": 120, "precipitation_mm": 12},
            {"timestamp_minutes": 180, "precipitation_mm": 25},
            {"timestamp_minutes": 240, "precipitation_mm": 8},
        ],
        "dt_minutes": 60,
        "initial_flow_cms": 210,
        "catchment_area_km2": 1200,
        "runoff_coefficient": 0.35,
        "response_time_hours": 8,
        "baseflow_cms": 120,
    }


def test_runoff_forecast_api_returns_future_hydrograph():
    response = client.post("/api/forecasts/runoff", json=payload())

    assert response.status_code == 200
    body = response.json()
    assert body["object_id"] == "gauge-keswick"
    assert body["model"] == "linear_reservoir"
    assert body["horizon_minutes"] == 240
    assert len(body["runoff"]) == 4
    assert body["summary"]["total_rainfall_mm"] == 45
    assert body["summary"]["peak_flow_cms"] > body["summary"]["current_flow_cms"]


def test_runoff_forecast_api_rejects_unknown_object():
    response = client.post("/api/forecasts/runoff", json=payload("missing-gauge"))

    assert response.status_code == 404
    assert response.json()["detail"] == "object not found"


def test_runoff_forecast_api_rejects_broken_time_grid():
    body = payload()
    body["rainfall"][1]["timestamp_minutes"] = 180
    response = client.post("/api/forecasts/runoff", json=body)

    assert response.status_code == 422
