import httpx

from hydropilot_api.llm import ChatMessage, ChatRequest, ProviderId, chat_completion, provider_catalog


def test_provider_catalog_contains_mainstream_and_local_providers():
    providers = {item.id for item in provider_catalog()}
    assert {
        ProviderId.OPENAI,
        ProviderId.ANTHROPIC,
        ProviderId.GEMINI,
        ProviderId.DEEPSEEK,
        ProviderId.SILICONFLOW,
        ProviderId.OPENROUTER,
        ProviderId.OLLAMA,
        ProviderId.CUSTOM_OPENAI,
    } <= providers


def test_openai_compatible_adapter():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://example.test/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer secret"
        return httpx.Response(200, json={
            "choices": [{"message": {"role": "assistant", "content": "mapped"}}],
            "usage": {"total_tokens": 12},
        })

    response = chat_completion(
        ChatRequest(
            provider=ProviderId.CUSTOM_OPENAI,
            base_url="https://example.test/v1",
            api_key="secret",
            model="demo-model",
            messages=[ChatMessage(role="user", content="hello")],
        ),
        transport=httpx.MockTransport(handler),
    )
    assert response.text == "mapped"
    assert response.usage == {"total_tokens": 12}


def test_anthropic_adapter_moves_system_prompt():
    def handler(request: httpx.Request) -> httpx.Response:
        body = __import__("json").loads(request.content)
        assert str(request.url) == "https://api.anthropic.com/v1/messages"
        assert request.headers["x-api-key"] == "secret"
        assert body["system"] == "GIS copilot"
        assert body["messages"] == [{"role": "user", "content": "hello"}]
        return httpx.Response(200, json={
            "content": [{"type": "text", "text": "anthropic-ok"}],
            "usage": {"input_tokens": 3, "output_tokens": 4},
        })

    response = chat_completion(
        ChatRequest(
            provider=ProviderId.ANTHROPIC,
            api_key="secret",
            model="claude-test",
            messages=[
                ChatMessage(role="system", content="GIS copilot"),
                ChatMessage(role="user", content="hello"),
            ],
        ),
        transport=httpx.MockTransport(handler),
    )
    assert response.text == "anthropic-ok"


def test_gemini_adapter_uses_native_generate_content():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://generativelanguage.googleapis.com/v1beta/models/gemini-test:generateContent"
        assert request.headers["x-goog-api-key"] == "secret"
        return httpx.Response(200, json={
            "candidates": [{"content": {"parts": [{"text": "gemini-ok"}]}}],
            "usageMetadata": {"totalTokenCount": 9},
        })

    response = chat_completion(
        ChatRequest(
            provider=ProviderId.GEMINI,
            api_key="secret",
            model="gemini-test",
            messages=[ChatMessage(role="user", content="hello")],
        ),
        transport=httpx.MockTransport(handler),
    )
    assert response.text == "gemini-ok"


def test_ollama_adapter_needs_no_api_key():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://127.0.0.1:11434/api/chat"
        return httpx.Response(200, json={
            "message": {"role": "assistant", "content": "ollama-ok"},
            "prompt_eval_count": 5,
            "eval_count": 6,
        })

    response = chat_completion(
        ChatRequest(
            provider=ProviderId.OLLAMA,
            model="qwen3",
            messages=[ChatMessage(role="user", content="hello")],
        ),
        transport=httpx.MockTransport(handler),
    )
    assert response.text == "ollama-ok"
    assert response.usage == {"prompt_eval_count": 5, "eval_count": 6}
