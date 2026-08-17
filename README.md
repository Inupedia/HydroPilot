# HydroPilot

HydroPilot is an AI-oriented water-network digital-twin demonstrator for flood-control and dispatch scenes. It combines a FastAPI backend, deterministic hydro models, Vue 3 + Cesium, and an Electron desktop shell.

## Start here — run the whole application

Do **not** start with `apps/web` alone unless you intentionally want frontend-only development. The Vue app depends on the HydroPilot API.

From the repository root, run the one-time setup:

```bash
npm run setup
```

Then start the complete desktop development stack:

```bash
npm run dev
```

That single command starts:

```text
Electron
├── local FastAPI backend (auto-started by Electron)
├── Vue/Vite renderer
└── Cesium water-network scene
```

If you prefer a normal browser instead of Electron, run:

```bash
npm run dev:web
```

That starts both services together:

```text
UI:       http://127.0.0.1:5173
API:      http://127.0.0.1:8000
API docs: http://127.0.0.1:8000/docs
```

Running only this command:

```bash
npm --prefix apps/web run dev
```

starts **only Vite** and therefore is not a complete HydroPilot runtime.

## What HydroPilot includes

- Sacramento public-data-derived demo fixture.
- Directed `hydro_object` / `hydro_relation` water-network model.
- Downstream traversal over `FLOWS_TO` relations.
- 0D reservoir mass balance and 1D Muskingum routing.
- FastAPI object, topology, release-scenario, and LLM APIs.
- Vue 3 + Cesium map-first interface and scenario timeline.
- Electron desktop shell that owns the local FastAPI sidecar lifecycle.
- Multi-provider LLM support: OpenAI, Anthropic, Gemini, DeepSeek, SiliconFlow, OpenRouter, Ollama, and custom OpenAI-compatible endpoints.
- Electron `safeStorage` for desktop API keys.
- GitHub Actions CI, Cesium visual acceptance, packaged desktop smoke tests, releases, and merged-branch cleanup.
- Optional non-blocking SFINCS tiny regression adapter.

## Backend-only development

If you intentionally want to work only on the API:

```bash
make api-dev
```

Then verify it:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/network/reach-001/downstream?max_hops=4
curl http://127.0.0.1:8000/api/llm/providers
```

Interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## LLM providers

HydroPilot separates providers from wire-protocol adapters so compatible vendors can share tested implementations.

| Provider | Adapter family | API key |
| --- | --- | --- |
| OpenAI | `openai-compatible` | required |
| Anthropic | `anthropic` | required |
| Google Gemini | `gemini` | required |
| DeepSeek | `openai-compatible` | required |
| SiliconFlow | `openai-compatible` | required |
| OpenRouter | `openai-compatible` | required |
| Ollama | `ollama` | none by default |
| Custom OpenAI-compatible | `openai-compatible` | configurable |

In the Electron app, configure provider/model/API key from the Copilot panel. Desktop secrets are stored through Electron `safeStorage`.

## Desktop runtime architecture

```text
HydroPilot Electron
├── Electron main process
│   ├── allocates an available loopback API port
│   ├── starts/stops FastAPI automatically
│   ├── exposes encrypted secret storage
│   └── serves/proxies the renderer and /api
├── Vue 3 renderer
│   └── CesiumJS water-network digital twin
├── hydropilot-api sidecar
└── demo data
```

In source development Electron launches Python directly. In packaged releases FastAPI is compiled into a PyInstaller sidecar, so end users do not need Python installed.

## Build a desktop package

Build the API sidecar first:

```bash
python -m pip install pyinstaller
pyinstaller --clean --noconfirm --onefile --name hydropilot-api \
  --paths apps/api/src \
  --paths packages/hydropilot-core/src \
  apps/api/desktop_entry.py
python scripts/stage_desktop_api.py
```

Then package Electron for the current OS:

```bash
npm --prefix apps/desktop run dist
```

Installers are written to `apps/desktop/release/`. GitHub Actions builds native macOS Apple Silicon, macOS Intel, Windows x64, and Linux x64 release assets.

## Tests

```bash
make verify
npm test
```

The repository also runs CI, real-browser Cesium visual acceptance, and packaged Electron smoke acceptance in GitHub Actions.

## Data policy

Only small, reviewable demo fixtures are committed. Raw public datasets, model outputs, generated caches, and secrets stay out of Git.

## Safety and scope

HydroPilot remains a demonstrator. It is not operational flood-control, reservoir-dispatch, emergency-warning, or engineering-design decision support.
