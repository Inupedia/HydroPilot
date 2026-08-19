from fastapi.testclient import TestClient

from hydropilot_api.main import app

client = TestClient(app)


def test_tool_api_returns_normalized_effective_arguments():
    response = client.post(
        "/api/tools/execute",
        json={"name": "trace_downstream", "arguments": {"object_id": "reach-001", "limit": 2}},
    )

    assert response.status_code == 200
    assert response.json()["arguments"] == {
        "object_id": "reach-001",
        "max_hops": 8,
        "offset": 0,
        "limit": 2,
    }


def test_tool_api_rejects_unknown_tool_argument_with_422():
    response = client.post(
        "/api/tools/execute",
        json={
            "name": "get_object",
            "arguments": {"object_id": "reservoir-shasta", "delete": True},
        },
    )

    assert response.status_code == 422
    assert "Extra inputs are not permitted" in response.json()["detail"]


def test_tool_api_rejects_unknown_top_level_request_field_with_422():
    response = client.post(
        "/api/tools/execute",
        json={
            "name": "get_object",
            "arguments": {"object_id": "reservoir-shasta"},
            "trusted": True,
        },
    )

    assert response.status_code == 422
