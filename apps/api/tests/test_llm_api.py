from fastapi.testclient import TestClient

from hydropilot_api.main import app


client = TestClient(app)


def test_llm_provider_catalog_api():
    response = client.get("/api/llm/providers")
    assert response.status_code == 200
    providers = {item["id"]: item for item in response.json()}
    assert providers["openai"]["adapter_family"] == "openai-compatible"
    assert providers["anthropic"]["adapter_family"] == "anthropic"
    assert providers["gemini"]["adapter_family"] == "gemini"
    assert providers["ollama"]["auth_required"] is False
