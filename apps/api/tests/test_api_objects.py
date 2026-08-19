from fastapi.testclient import TestClient

import hydropilot_api.main as main_module
from hydropilot_api.main import app

client = TestClient(app)


def constant_hydrograph(flow_cms: float, duration_minutes: int) -> list[dict[str, float | int]]:
    return [
        {"timestamp_minutes": 0, "flow_cms": flow_cms},
        {"timestamp_minutes": duration_minutes, "flow_cms": flow_cms},
    ]


def scenario_payload(*, reservoir_id: str = "reservoir-shasta") -> dict:
    return {
        "reservoir_id": reservoir_id,
        "duration_minutes": 60,
        "dt_minutes": 30,
        "max_hops": 2,
        "inflow_hydrograph": constant_hydrograph(500, 60),
        "release_hydrograph": constant_hydrograph(900, 60),
    }


def test_list_objects_supports_type_filter():
    response = client.get("/api/objects", params={"object_type": "reservoir"})
    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == ["reservoir-shasta"]


def test_downstream_endpoint_returns_hop_aware_network():
    response = client.get("/api/network/reach-001/downstream", params={"max_hops": 3})
    assert response.status_code == 200
    assert [(item["object_id"], item["hop"]) for item in response.json()] == [("reach-002", 1), ("reach-003", 2), ("reach-004", 3)]


def test_release_scenario_requires_explicit_inflow_and_release_boundaries():
    missing_release = client.post(
        "/api/scenarios/release",
        json={
            "duration_minutes": 60,
            "dt_minutes": 30,
            "max_hops": 2,
            "inflow_hydrograph": constant_hydrograph(500, 60),
        },
    )
    assert missing_release.status_code == 422

    missing_inflow = client.post(
        "/api/scenarios/release",
        json={
            "duration_minutes": 60,
            "dt_minutes": 30,
            "max_hops": 2,
            "release_hydrograph": constant_hydrograph(900, 60),
        },
    )
    assert missing_inflow.status_code == 422


def test_release_scenario_maps_service_validation_error_to_422(monkeypatch):
    def reject_scenario(repo, request):
        raise ValueError("branching FLOWS_TO topology is unsupported at reach-001")

    monkeypatch.setattr(main_module, "run_release_scenario", reject_scenario)

    response = client.post("/api/scenarios/release", json=scenario_payload())

    assert response.status_code == 422
    assert response.json() == {"detail": "branching FLOWS_TO topology is unsupported at reach-001"}


def test_release_scenario_missing_reservoir_remains_404():
    response = client.post(
        "/api/scenarios/release",
        json=scenario_payload(reservoir_id="reservoir-missing"),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "object not found: reservoir-missing"}


def test_release_scenario_persists_computed_state_shape():
    response = client.post("/api/scenarios/release", json=scenario_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["scenario_id"] == "scenario-release"
    variables = {state["variable"] for state in body["states"]}
    assert {"storage", "inflow", "release", "flow"}.issubset(variables)
    flow_objects = {state["object_id"] for state in body["states"] if state["variable"] == "flow"}
    assert {"reach-001", "reach-002"}.issubset(flow_objects)


def test_release_scenario_remains_stable_across_supported_network_depth():
    response = client.post(
        "/api/scenarios/release",
        json={
            "duration_minutes": 180,
            "dt_minutes": 30,
            "max_hops": 12,
            "inflow_hydrograph": constant_hydrograph(1200, 180),
            "release_hydrograph": constant_hydrograph(2200, 180),
        },
    )
    assert response.status_code == 200
    flow_states = [state for state in response.json()["states"] if state["variable"] == "flow"]
    assert {state["object_id"] for state in flow_states} >= {"reach-001", "reach-002", "reach-007", "reach-013"}
    assert all(state["value"] >= 0 for state in flow_states)
