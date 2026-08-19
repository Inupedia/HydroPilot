from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import httpx
from pydantic import BaseModel, Field


class AdapterFamily(StrEnum):
    OPENAI_COMPATIBLE = "openai-compatible"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class ProviderId(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    SILICONFLOW = "siliconflow"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    CUSTOM_OPENAI = "custom-openai"


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    provider: ProviderId
    model: str = Field(min_length=1)
    messages: list[ChatMessage] = Field(min_length=1)
    api_key: str | None = Field(default=None, repr=False)
    base_url: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=131072)


class ChatResponse(BaseModel):
    provider: ProviderId
    model: str
    text: str
    usage: dict[str, Any] | None = None


class FunctionToolDefinition(BaseModel):
    name: str = Field(min_length=1)
    description: str
    parameters: dict[str, Any]


class ToolChatRequest(ChatRequest):
    tools: list[FunctionToolDefinition] = Field(min_length=1)


class ToolCall(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: dict[str, Any]


class ToolChatResponse(BaseModel):
    provider: ProviderId
    model: str
    text: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: dict[str, Any] | None = None


class ProviderSummary(BaseModel):
    id: ProviderId
    name: str
    adapter_family: AdapterFamily
    default_base_url: str | None
    api_key_env: str | None
    auth_required: bool
    model_examples: list[str]


@dataclass(frozen=True)
class ProviderDefinition:
    id: ProviderId
    name: str
    adapter_family: AdapterFamily
    default_base_url: str | None
    api_key_env: str | None
    auth_required: bool = True
    model_examples: tuple[str, ...] = ()


PROVIDERS: dict[ProviderId, ProviderDefinition] = {
    ProviderId.OPENAI: ProviderDefinition(
        id=ProviderId.OPENAI,
        name="OpenAI",
        adapter_family=AdapterFamily.OPENAI_COMPATIBLE,
        default_base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        model_examples=("gpt-5.1", "gpt-5-mini"),
    ),
    ProviderId.ANTHROPIC: ProviderDefinition(
        id=ProviderId.ANTHROPIC,
        name="Anthropic",
        adapter_family=AdapterFamily.ANTHROPIC,
        default_base_url="https://api.anthropic.com/v1",
        api_key_env="ANTHROPIC_API_KEY",
        model_examples=("claude-sonnet-4",),
    ),
    ProviderId.GEMINI: ProviderDefinition(
        id=ProviderId.GEMINI,
        name="Google Gemini",
        adapter_family=AdapterFamily.GEMINI,
        default_base_url="https://generativelanguage.googleapis.com/v1beta",
        api_key_env="GEMINI_API_KEY",
        model_examples=("gemini-3.5-flash",),
    ),
    ProviderId.DEEPSEEK: ProviderDefinition(
        id=ProviderId.DEEPSEEK,
        name="DeepSeek",
        adapter_family=AdapterFamily.OPENAI_COMPATIBLE,
        default_base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
        model_examples=("deepseek-v4-flash", "deepseek-v4-pro"),
    ),
    ProviderId.SILICONFLOW: ProviderDefinition(
        id=ProviderId.SILICONFLOW,
        name="SiliconFlow",
        adapter_family=AdapterFamily.OPENAI_COMPATIBLE,
        default_base_url="https://api.siliconflow.cn/v1",
        api_key_env="SILICONFLOW_API_KEY",
        model_examples=("Pro/zai-org/GLM-4.7",),
    ),
    ProviderId.OPENROUTER: ProviderDefinition(
        id=ProviderId.OPENROUTER,
        name="OpenRouter",
        adapter_family=AdapterFamily.OPENAI_COMPATIBLE,
        default_base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        model_examples=("openai/gpt-5.1", "anthropic/claude-sonnet-4"),
    ),
    ProviderId.OLLAMA: ProviderDefinition(
        id=ProviderId.OLLAMA,
        name="Ollama",
        adapter_family=AdapterFamily.OLLAMA,
        default_base_url="http://127.0.0.1:11434",
        api_key_env=None,
        auth_required=False,
        model_examples=("qwen3", "gpt-oss:20b"),
    ),
    ProviderId.CUSTOM_OPENAI: ProviderDefinition(
        id=ProviderId.CUSTOM_OPENAI,
        name="Custom OpenAI-compatible",
        adapter_family=AdapterFamily.OPENAI_COMPATIBLE,
        default_base_url=None,
        api_key_env="HYDROPILOT_LLM_API_KEY",
        model_examples=(),
    ),
}


class LLMProviderError(RuntimeError):
    pass


def provider_catalog() -> list[ProviderSummary]:
    return [
        ProviderSummary(
            id=item.id,
            name=item.name,
            adapter_family=item.adapter_family,
            default_base_url=item.default_base_url,
            api_key_env=item.api_key_env,
            auth_required=item.auth_required,
            model_examples=list(item.model_examples),
        )
        for item in PROVIDERS.values()
    ]


def _resolve_credentials(request: ChatRequest) -> tuple[ProviderDefinition, str, str | None]:
    provider = PROVIDERS[request.provider]
    base_url = (request.base_url or provider.default_base_url or "").rstrip("/")
    if not base_url:
        raise LLMProviderError("base_url is required for custom OpenAI-compatible providers")

    api_key = request.api_key
    if not api_key and provider.api_key_env:
        api_key = os.getenv(provider.api_key_env)
    if provider.auth_required and not api_key:
        raise LLMProviderError(f"API key is required for {provider.name}")
    return provider, base_url, api_key


def _openai_payload(request: ChatRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": request.model,
        "messages": [message.model_dump() for message in request.messages],
        "stream": False,
    }
    if request.temperature is not None:
        payload["temperature"] = request.temperature
    if request.max_tokens is not None:
        payload["max_tokens"] = request.max_tokens
    return payload


def _openai_tool_payload(request: ToolChatRequest) -> dict[str, Any]:
    payload = _openai_payload(request)
    payload["tools"] = [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in request.tools
    ]
    payload["tool_choice"] = "auto"
    return payload


def _anthropic_payload(request: ChatRequest) -> dict[str, Any]:
    system_parts = [m.content for m in request.messages if m.role == "system"]
    messages = [
        {"role": m.role, "content": m.content}
        for m in request.messages
        if m.role in {"user", "assistant"}
    ]
    payload: dict[str, Any] = {
        "model": request.model,
        "messages": messages,
        "max_tokens": request.max_tokens or 2048,
    }
    if system_parts:
        payload["system"] = "\n\n".join(system_parts)
    if request.temperature is not None:
        payload["temperature"] = request.temperature
    return payload


def _gemini_payload(request: ChatRequest) -> dict[str, Any]:
    system_parts = [m.content for m in request.messages if m.role == "system"]
    contents = []
    for message in request.messages:
        if message.role == "system":
            continue
        role = "model" if message.role == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": message.content}]})

    payload: dict[str, Any] = {"contents": contents}
    if system_parts:
        payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
    generation_config: dict[str, Any] = {}
    if request.temperature is not None:
        generation_config["temperature"] = request.temperature
    if request.max_tokens is not None:
        generation_config["maxOutputTokens"] = request.max_tokens
    if generation_config:
        payload["generationConfig"] = generation_config
    return payload


def _ollama_payload(request: ChatRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": request.model,
        "messages": [message.model_dump() for message in request.messages],
        "stream": False,
    }
    options: dict[str, Any] = {}
    if request.temperature is not None:
        options["temperature"] = request.temperature
    if request.max_tokens is not None:
        options["num_predict"] = request.max_tokens
    if options:
        payload["options"] = options
    return payload


def _extract_openai(data: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMProviderError("OpenAI-compatible provider returned an unexpected response") from exc
    return str(text), data.get("usage")


def _extract_openai_tool_round(data: dict[str, Any]) -> tuple[str | None, list[ToolCall], dict[str, Any] | None]:
    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMProviderError("OpenAI-compatible provider returned an unexpected tool response") from exc
    if not isinstance(message, dict):
        raise LLMProviderError("OpenAI-compatible provider returned an unexpected tool response")

    raw_content = message.get("content")
    if raw_content is not None and not isinstance(raw_content, str):
        raise LLMProviderError("OpenAI-compatible provider returned invalid assistant text")
    text = raw_content if isinstance(raw_content, str) and raw_content.strip() else None

    raw_tool_calls = message.get("tool_calls", []) or []
    if not isinstance(raw_tool_calls, list):
        raise LLMProviderError("OpenAI-compatible provider returned invalid tool calls")

    tool_calls: list[ToolCall] = []
    for item in raw_tool_calls:
        if not isinstance(item, dict):
            raise LLMProviderError("OpenAI-compatible provider returned invalid tool call")
        call_id = item.get("id")
        if not isinstance(call_id, str) or not call_id.strip():
            raise LLMProviderError("OpenAI-compatible provider returned tool call without id")
        if item.get("type") != "function":
            raise LLMProviderError("OpenAI-compatible provider returned unsupported tool call type")
        function = item.get("function")
        if not isinstance(function, dict):
            raise LLMProviderError("OpenAI-compatible provider returned invalid tool call function")
        name = function.get("name")
        if not isinstance(name, str) or not name.strip():
            raise LLMProviderError("OpenAI-compatible provider returned tool call without function name")
        raw_arguments = function.get("arguments")
        if not isinstance(raw_arguments, str):
            raise LLMProviderError("OpenAI-compatible tool call arguments must be a JSON string")
        try:
            arguments = json.loads(raw_arguments)
        except json.JSONDecodeError as exc:
            raise LLMProviderError("OpenAI-compatible tool call arguments are not valid JSON") from exc
        if not isinstance(arguments, dict):
            raise LLMProviderError("OpenAI-compatible tool call arguments must decode to a JSON object")
        tool_calls.append(ToolCall(id=call_id, name=name, arguments=arguments))

    if text is None and not tool_calls:
        raise LLMProviderError("OpenAI-compatible provider returned no text or tool calls")
    return text, tool_calls, data.get("usage")


def _extract_anthropic(data: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    blocks = data.get("content", [])
    text = "".join(str(block.get("text", "")) for block in blocks if block.get("type") == "text")
    if not text:
        raise LLMProviderError("Anthropic returned no text content")
    return text, data.get("usage")


def _extract_gemini(data: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMProviderError("Gemini returned an unexpected response") from exc
    text = "".join(str(part.get("text", "")) for part in parts)
    if not text:
        raise LLMProviderError("Gemini returned no text content")
    return text, data.get("usageMetadata")


def _extract_ollama(data: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    try:
        text = data["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise LLMProviderError("Ollama returned an unexpected response") from exc
    usage = {
        key: data[key]
        for key in ("prompt_eval_count", "eval_count", "total_duration")
        if key in data
    }
    return str(text), usage or None


def chat_completion(request: ChatRequest, *, transport: httpx.BaseTransport | None = None) -> ChatResponse:
    provider, base_url, api_key = _resolve_credentials(request)
    headers = {"content-type": "application/json"}

    if provider.adapter_family == AdapterFamily.OPENAI_COMPATIBLE:
        url = f"{base_url}/chat/completions"
        headers["authorization"] = f"Bearer {api_key}"
        payload = _openai_payload(request)
        extractor = _extract_openai
    elif provider.adapter_family == AdapterFamily.ANTHROPIC:
        url = f"{base_url}/messages"
        headers["x-api-key"] = str(api_key)
        headers["anthropic-version"] = "2023-06-01"
        payload = _anthropic_payload(request)
        extractor = _extract_anthropic
    elif provider.adapter_family == AdapterFamily.GEMINI:
        model = request.model.removeprefix("models/")
        url = f"{base_url}/models/{model}:generateContent"
        headers["x-goog-api-key"] = str(api_key)
        payload = _gemini_payload(request)
        extractor = _extract_gemini
    elif provider.adapter_family == AdapterFamily.OLLAMA:
        url = f"{base_url}/api/chat"
        payload = _ollama_payload(request)
        extractor = _extract_ollama
    else:  # pragma: no cover - enum guards this branch
        raise LLMProviderError(f"unsupported adapter family: {provider.adapter_family}")

    try:
        with httpx.Client(timeout=60.0, transport=transport) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        message = exc.response.text[:500]
        raise LLMProviderError(f"{provider.name} request failed ({exc.response.status_code}): {message}") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise LLMProviderError(f"{provider.name} request failed: {exc}") from exc

    text, usage = extractor(data)
    return ChatResponse(provider=request.provider, model=request.model, text=text, usage=usage)


def tool_chat_round(
    request: ToolChatRequest,
    *,
    transport: httpx.BaseTransport | None = None,
) -> ToolChatResponse:
    provider_definition = PROVIDERS[request.provider]
    if provider_definition.adapter_family is not AdapterFamily.OPENAI_COMPATIBLE:
        raise LLMProviderError("tool calling is currently supported only for OpenAI-compatible providers")

    provider, base_url, api_key = _resolve_credentials(request)
    url = f"{base_url}/chat/completions"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {api_key}",
    }
    payload = _openai_tool_payload(request)

    try:
        with httpx.Client(timeout=60.0, transport=transport) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        message = exc.response.text[:500]
        raise LLMProviderError(f"{provider.name} request failed ({exc.response.status_code}): {message}") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise LLMProviderError(f"{provider.name} request failed: {exc}") from exc

    text, tool_calls, usage = _extract_openai_tool_round(data)
    return ToolChatResponse(
        provider=request.provider,
        model=request.model,
        text=text,
        tool_calls=tool_calls,
        usage=usage,
    )
