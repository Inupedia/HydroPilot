from fastapi.testclient import TestClient

from hydropilot_api.main import app


def test_flow_forecast_api_returns_future_points_and_peak_summary():
    client = TestClient(app)
    response = client.post(
        "/api/forecasts/flow",
        json={
            "object_id": "gauge-keswick",
            "history": [
                {"timestamp_minutes": -60, "flow_cms": 180},
                {"timestamp_minutes": -30, "flow_cms": 195},
                {"timestamp_minutes": 0, "flow_cms": 210},
            ],
            "horizon_minutes": 60,
            "dt_minutes": 30,
            "damping": 0.5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["object_id"] == "gauge-keswick"
    assert payload["model"] == "damped_trend"
    assert [point["timestamp_minutes"] for point in payload["forecast"]] == [30, 60]
    assert [point["flow_cms"] for point in payload["forecast"]] == [225.0, 232.5]
    assert payload["summary"]["current_flow_cms"] == 210.0
    assert payload["summary"]["peak_flow_cms"] == 232.5
    assert payload["summary"]["peak_timestamp_minutes"] == 60
    assert payload["summary"]["trend"] == "rising"


def test_flow_forecast_api_rejects_unknown_object():
    client = TestClient(app)
    response = client.post(
        "/api/forecasts/flow",
        json={
            "object_id": "missing-object",
            "history": [
                {"timestamp_minutes": -30, "flow_cms": 100},
                {"timestamp_minutes": 0, "flow_cms": 120},
            ],
            "horizon_minutes": 60,
            "dt_minutes": 30,
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "object not found"}
