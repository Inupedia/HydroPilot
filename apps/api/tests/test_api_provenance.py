from fastapi.testclient import TestClient

from hydropilot_api.main import app

client = TestClient(app)


def test_detailed_object_api_exposes_solver_property_provenance():
    response = client.get("/api/objects/reservoir-shasta")

    assert response.status_code == 200
    body = response.json()
    provenance = body["property_provenance"]

    for property_name in ["initial_storage_m3", "max_storage_m3", "initial_level_m"]:
        if property_name not in body["properties"]:
            continue
        assert provenance[property_name]["origin"] == "model_assumption"
        assert provenance[property_name]["source"] == "HydroPilot Sacramento demo configuration"
        assert "authoritative" in provenance[property_name]["note"].lower()
        assert "operational" in provenance[property_name]["note"].lower()
