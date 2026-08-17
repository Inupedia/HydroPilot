from fastapi.testclient import TestClient
from hydropilot_api.main import app

client = TestClient(app)


def test_list_objects_supports_type_filter():
    response = client.get("/api/objects", params={"object_type": "reservoir"})
    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == ["reservoir-shasta"]


def test_downstream_endpoint_returns_hop_aware_network():
    response = client.get("/api/network/reach-001/downstream", params={"max_hops": 3})
    assert response.status_code == 200
    assert [(item["object_id"], item["hop"]) for item in response.json()] == [("reach-002", 1), ("reach-003", 2), ("reach-004", 3)]


def test_release_scenario_persists_computed_state_shape():
    response = client.post("/api/scenarios/release", json={"release_cms": 900, "duration_minutes": 60, "dt_minutes": 30, "max_hops": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["scenario_id"] == "scenario-release"
    variables = {state["variable"] for state in body["states"]}
    assert {"storage", "level", "flow"}.issubset(variables)
