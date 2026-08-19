from fastapi.testclient import TestClient

from hydropilot_api.main import app

client = TestClient(app)


def test_tools_catalog_exposes_only_read_only_hydro_tools():
    response = client.get("/api/tools")

    assert response.status_code == 200
    body = response.json()
    assert [item["name"] for item in body] == [
        "get_object",
        "list_constraints",
        "list_curves",
        "list_objects",
        "trace_downstream",
    ]
    assert all(item["read_only"] is True for item in body)
    assert all(item["input_schema"]["type"] == "object" for item in body)


def test_tool_execution_reads_real_demo_object():
    response = client.post(
        "/api/tools/execute",
        json={"name": "get_object", "arguments": {"object_id": "reservoir-shasta"}},
    )

    assert response.status_code == 200
    assert response.json()["result"]["id"] == "reservoir-shasta"


def test_tool_execution_lists_real_demo_reservoir_objects():
    response = client.post(
        "/api/tools/execute",
        json={"name": "list_objects", "arguments": {"object_type": "reservoir"}},
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["result"]] == ["reservoir-shasta"]


def test_tool_execution_can_read_honest_empty_demo_curves_and_constraints():
    curves = client.post(
        "/api/tools/execute",
        json={"name": "list_curves", "arguments": {"object_id": "reservoir-shasta"}},
    )
    constraints = client.post(
        "/api/tools/execute",
        json={"name": "list_constraints", "arguments": {"object_id": "reservoir-shasta"}},
    )

    assert curves.status_code == 200
    assert curves.json()["result"] == []
    assert constraints.status_code == 200
    assert constraints.json()["result"] == []


def test_tool_execution_maps_missing_object_to_404():
    response = client.post(
        "/api/tools/execute",
        json={"name": "get_object", "arguments": {"object_id": "missing-object"}},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "object not found: missing-object"}


def test_tool_execution_maps_unknown_tool_and_bad_arguments_to_422():
    unknown = client.post(
        "/api/tools/execute",
        json={"name": "delete_everything", "arguments": {}},
    )
    invalid = client.post(
        "/api/tools/execute",
        json={"name": "get_object", "arguments": {}},
    )

    assert unknown.status_code == 422
    assert "unknown hydro tool" in unknown.json()["detail"]
    assert invalid.status_code == 422
