import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import hydropilot_api.main as main_module
from hydropilot_api.agent import AgentToolExecution, ReadOnlyAgentResponse
from hydropilot_api.llm import LLMProviderError, ProviderId
from hydropilot_api.main import app
from hydropilot_api.tools import HydroToolRequest

client = TestClient(app)


def payload(**overrides):
    value = {
        "provider": "custom-openai",
        "base_url": "https://example.test/v1",
        "api_key": "secret",
        "model": "demo-model",
        "messages": [{"role": "user", "content": "Inspect reservoir-shasta"}],
        "max_tool_rounds": 4,
    }
    value.update(overrides)
    return value


def test_agent_endpoint_returns_service_result_and_uses_server_repository(monkeypatch):
    captured = {}

    def fake_agent(repository, request):
        captured["repository"] = repository
        captured["request"] = request
        return ReadOnlyAgentResponse(
            provider=ProviderId.CUSTOM_OPENAI,
            model="demo-model",
            text="Shasta is available.",
            tool_executions=[
                AgentToolExecution(
                    call_id="call_1",
                    name="get_object",
                    arguments={"object_id": "reservoir-shasta"},
                    result={"id": "reservoir-shasta"},
                )
            ],
            provider_rounds=2,
        )

    monkeypatch.setattr(main_module, "run_read_only_agent", fake_agent)

    response = client.post("/api/agent/chat", json=payload())

    assert response.status_code == 200
    assert response.json() == {
        "provider": "custom-openai",
        "model": "demo-model",
        "text": "Shasta is available.",
        "tool_executions": [
            {
                "call_id": "call_1",
                "name": "get_object",
                "arguments": {"object_id": "reservoir-shasta"},
                "result": {"id": "reservoir-shasta"},
            }
        ],
        "provider_rounds": 2,
    }
    assert captured["repository"].get_object("reservoir-shasta") is not None
    assert captured["request"].model == "demo-model"


def test_agent_endpoint_maps_missing_tool_object_to_404(monkeypatch):
    def missing_object(repository, request):
        raise KeyError("reservoir-missing")

    monkeypatch.setattr(main_module, "run_read_only_agent", missing_object)

    response = client.post("/api/agent/chat", json=payload())

    assert response.status_code == 404
    assert response.json() == {"detail": "object not found: reservoir-missing"}


def test_agent_endpoint_maps_deterministic_agent_error_to_422(monkeypatch):
    def reject_agent(repository, request):
        raise ValueError("read-only agent exceeded max tool rounds")

    monkeypatch.setattr(main_module, "run_read_only_agent", reject_agent)

    response = client.post("/api/agent/chat", json=payload())

    assert response.status_code == 422
    assert response.json() == {"detail": "read-only agent exceeded max tool rounds"}


def test_agent_endpoint_maps_internal_tool_validation_error_to_422(monkeypatch):
    with pytest.raises(ValidationError) as exc_info:
        HydroToolRequest.model_validate({"name": "", "arguments": {}})
    validation_error = exc_info.value

    def reject_tool_args(repository, request):
        raise validation_error

    monkeypatch.setattr(main_module, "run_read_only_agent", reject_tool_args)

    response = client.post("/api/agent/chat", json=payload())

    assert response.status_code == 422
    assert "String should have at least 1 character" in response.json()["detail"]


def test_agent_endpoint_maps_missing_credentials_to_400(monkeypatch):
    def missing_key(repository, request):
        raise LLMProviderError("API key is required for OpenAI")

    monkeypatch.setattr(main_module, "run_read_only_agent", missing_key)

    response = client.post("/api/agent/chat", json=payload())

    assert response.status_code == 400
    assert response.json() == {"detail": "API key is required for OpenAI"}


def test_agent_endpoint_maps_upstream_provider_failure_to_502(monkeypatch):
    def provider_down(repository, request):
        raise LLMProviderError("OpenAI request failed (503): unavailable")

    monkeypatch.setattr(main_module, "run_read_only_agent", provider_down)

    response = client.post("/api/agent/chat", json=payload())

    assert response.status_code == 502
    assert response.json() == {"detail": "OpenAI request failed (503): unavailable"}


def test_agent_endpoint_rejects_caller_supplied_tools_before_service_execution(monkeypatch):
    service_called = False

    def should_not_run(repository, request):
        nonlocal service_called
        service_called = True
        raise AssertionError("service should not run")

    monkeypatch.setattr(main_module, "run_read_only_agent", should_not_run)

    response = client.post(
        "/api/agent/chat",
        json=payload(tools=[{"name": "run_release_scenario"}]),
    )

    assert response.status_code == 422
    assert service_called is False


def test_agent_endpoint_rejects_unsupported_provider_before_network():
    response = client.post(
        "/api/agent/chat",
        json=payload(provider="anthropic"),
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "read-only agent currently supports only OpenAI-compatible providers"
    }
