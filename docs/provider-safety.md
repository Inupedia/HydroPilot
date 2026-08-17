# Provider credential boundary

V0.2 never writes provider credentials into the repository or demo fixture.

The backend resolves credentials in this order:

1. an explicit local `ChatRequest.api_key` value;
2. the provider-specific environment variable declared in the provider registry.

Ollama does not require an API key by default. Custom OpenAI-compatible endpoints require an explicit base URL.

A later Electron settings UI should persist API keys with OS-backed encryption (Electron `safeStorage`) and only pass decrypted credentials to the loopback API for the lifetime of a request. Plain-text localStorage persistence is out of scope and should not be introduced.
