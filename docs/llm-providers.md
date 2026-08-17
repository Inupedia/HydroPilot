# LLM provider architecture

HydroPilot keeps GIS/business logic independent from vendor SDKs.

```text
GIS Copilot / Agent
        |
        v
  ChatRequest
        |
        v
 Provider Registry
        |
        +-- openai-compatible --> OpenAI / DeepSeek / SiliconFlow / OpenRouter / custom gateways
        +-- anthropic ---------> Anthropic Messages API
        +-- gemini ------------> Gemini generateContent API
        +-- ollama ------------> Ollama local chat API
```

The registry owns provider identity, default endpoint, credential environment-variable name, adapter family, and model examples. Adapters own wire-format translation and response parsing.

This follows the same general separation used by multi-provider desktop clients such as Cherry Studio: provider identity and endpoint selection are resolved separately from the adapter family that actually performs the request.

## V0.2 scope

V0.2 implements non-streaming text chat as the stable common denominator. The boundary is intentionally designed so the next capabilities can be added without changing water-network services:

- streaming responses;
- tool/function calling for PostGIS and Cesium tools;
- structured output for GIS intent / visualization DSL;
- provider model discovery;
- encrypted Electron credential persistence;
- per-model capability metadata.

Provider API keys may be supplied through their documented environment variables or explicitly on a local request. Never commit keys to Git.
