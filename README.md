# HydroPilot

HydroPilot is a water-network digital twin demonstrator for flood-control and dispatch scenes.

V0.1 proves the foundation: public water-network data, directed topology, simple deterministic hydro models, APIs, and a Cesium map-first UI. V0.2 adds a self-contained Electron desktop runtime, GitHub Release installers, and a provider-neutral LLM boundary for the GIS copilot track.

## What HydroPilot includes

- Sacramento public-data-derived demo fixture.
- `hydro_object` / `hydro_relation` domain model.
- Directed downstream traversal over `FLOWS_TO` relations.
- 0D reservoir mass balance.
- 1D Muskingum river routing.
- FastAPI object, topology, release-scenario, and LLM APIs.
- Vue 3 + Cesium water-network viewer.
- Timeline-driven scenario state.
- Electron desktop shell with local API sidecar management.
- Desktop-local same-origin proxy so the renderer does not depend on a fixed API port.
- Multi-provider LLM registry inspired by Cherry Studio's provider/adapter separation.
- GitHub Actions quality gates, packaged Electron Cesium smoke testing, and tagged GitHub Releases.
- Optional non-blocking SFINCS tiny regression adapter.

## Web/API quickstart

```bash
make core-test
make api-test
make verify
make api-dev
```

API smoke:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/network/reach-001/downstream?max_hops=4
curl http://localhost:8000/api/llm/providers
```

Web app:

```bash
cd apps/web
npm install
npm run dev
```

## LLM providers

HydroPilot separates a provider from its wire-protocol adapter. This lets multiple vendors share one tested adapter while native APIs keep their own request/response mapping.

| Provider | Adapter family | Default API key environment variable |
| --- | --- | --- |
| OpenAI | `openai-compatible` | `OPENAI_API_KEY` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` |
| Google Gemini | `gemini` | `GEMINI_API_KEY` |
| DeepSeek | `openai-compatible` | `DEEPSEEK_API_KEY` |
| SiliconFlow | `openai-compatible` | `SILICONFLOW_API_KEY` |
| OpenRouter | `openai-compatible` | `OPENROUTER_API_KEY` |
| Ollama | `ollama` | none |
| Custom OpenAI-compatible | `openai-compatible` | `HYDROPILOT_LLM_API_KEY` |

Example request:

```bash
export SILICONFLOW_API_KEY='...'

curl http://localhost:8000/api/llm/chat \
  -H 'content-type: application/json' \
  -d '{
    "provider": "siliconflow",
    "model": "Pro/zai-org/GLM-4.7",
    "messages": [
      {"role": "system", "content": "You are the HydroPilot GIS copilot."},
      {"role": "user", "content": "Summarize the current water-network scene."}
    ]
  }'
```

`base_url` and `api_key` can also be supplied per request. The `custom-openai` provider requires an explicit `base_url` unless it is wrapped by a future desktop provider-settings store. API keys must not be committed to the repository.

The current provider layer is intentionally small: OpenAI-compatible vendors reuse one adapter; Anthropic uses `/v1/messages`; Gemini uses native `generateContent`; Ollama uses `/api/chat`. Tool calling, streaming, model discovery, and encrypted desktop credential persistence can be layered on this boundary without changing GIS/business logic.

## Electron desktop development

Install the Python API dependencies once:

```bash
python -m pip install -e packages/hydropilot-core -e apps/api
```

Install frontend and desktop dependencies:

```bash
npm --prefix apps/web install
npm --prefix apps/desktop install
```

Run the desktop application in development mode:

```bash
npm --prefix apps/desktop run dev
```

Electron starts and owns the local FastAPI process. The renderer remains Vue + Cesium; in development it uses the Vite dev server.

## Build a self-contained desktop package

The packaged application embeds a PyInstaller FastAPI sidecar, the Cesium/Vue production build, and the Sacramento demo fixture. Build the sidecar first:

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
npm --prefix apps/web install
npm --prefix apps/desktop install
npm --prefix apps/desktop run dist
```

Installers are written to `apps/desktop/release/`.

The `Desktop` GitHub Actions workflow supports packaged runtime acceptance and manual cross-platform packaging. Its Linux acceptance job launches the packaged Electron binary under Chromium/Xvfb and only passes after a real Cesium canvas and all 24 demo objects are visible.

## GitHub Releases

A version tag now represents a desktop release. Push a tag such as:

```bash
git tag v0.2.0
git push origin v0.2.0
```

The `Release` workflow builds the FastAPI sidecar and Electron installers independently on macOS, Windows, and Linux, then creates a GitHub Release and attaches the generated `.dmg` / `.zip`, `.exe` / `.zip`, and `.AppImage` / `.tar.gz` assets. The Electron package version is derived from the tag, so later `v0.x.y` releases do not require a manual version edit before packaging.

## Desktop runtime architecture

```text
HydroPilot Electron
├── Electron main process
│   ├── allocates an available loopback API port
│   ├── starts/stops the packaged FastAPI sidecar
│   └── serves the renderer and proxies /api to FastAPI
├── Vue 3 renderer
│   └── CesiumJS water-network digital twin
├── packaged hydropilot-api executable
└── packaged demo data
```

The packaged renderer is served from an Electron-owned loopback HTTP server rather than `file://`. This preserves normal Cesium asset loading and gives the renderer a same-origin `/api` path without exposing a hard-coded service port.

## Data policy

Only small, reviewable demo fixtures are committed. Raw public datasets, model outputs, generated caches, and secrets stay out of Git.

## Safety and scope

HydroPilot remains a demonstrator. It is not operational flood-control, reservoir-dispatch, emergency warning, or engineering-design decision support.
