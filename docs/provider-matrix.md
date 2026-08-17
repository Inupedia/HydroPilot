# Provider support matrix

| Provider | Text chat | Native adapter | OpenAI-compatible | Local |
| --- | --- | --- | --- | --- |
| OpenAI | yes | no | yes | no |
| Anthropic | yes | yes | no | no |
| Google Gemini | yes | yes | no | no |
| DeepSeek | yes | no | yes | no |
| SiliconFlow | yes | no | yes | no |
| OpenRouter | yes | no | yes | no |
| Ollama | yes | yes | no | yes |
| Custom OpenAI-compatible | yes | no | yes | depends |

V0.2 establishes the common provider boundary. Streaming, tool calling, structured GIS intent output, model discovery, embeddings, image models, and reranking are planned as capability flags rather than separate provider implementations.
