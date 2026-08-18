# HydroPilot

**AI-native water-network digital twin desktop application for flood-control and dispatch demonstrations.**

HydroPilot v0.3 uses **React + CesiumJS + Tauri 2** for the desktop client and keeps the existing **FastAPI + Python hydrologic core** as a local sidecar service. The previous Vue/Electron client has been retired.

## What works

- real Cesium 3D viewer with a Sacramento public-data demo fixture;
- directed water-network topology (`FLOWS_TO`) and downstream-chain highlighting;
- 0D reservoir mass-balance model;
- 1D Muskingum routing with timeline playback;
- AI Copilot with guided map commands;
- LLM providers: OpenAI, Anthropic, Gemini, DeepSeek, SiliconFlow, OpenRouter, Ollama, and custom OpenAI-compatible endpoints;
- OS credential-store protection for desktop LLM API keys;
- packaged FastAPI sidecar with a dynamically allocated loopback port;
- GitHub Actions browser acceptance, native Tauri build smoke, and four-platform Releases.

> HydroPilot is currently a public-data engineering demonstrator, not operational flood-control decision support.

## Repository layout

```text
HydroPilot/
├── apps/
│   ├── api/                  # FastAPI local service
│   └── studio/               # React + Cesium + Tauri 2 desktop app
│       ├── src/              # React UI and Cesium renderer
│       └── src-tauri/        # Rust desktop shell / sidecar lifecycle
├── packages/
│   └── hydropilot-core/      # Reservoir + Muskingum model core
├── data/demo/                # Small public demonstration fixture
└── scripts/                  # dev / sidecar / fixture tooling
```

## Development

Prerequisites:

- Python 3.12+
- Node.js 22+
- Rust stable (`cargo` and `rustc`)
- platform prerequisites required by Tauri 2 (Xcode Command Line Tools on macOS; MSVC/WebView2 on Windows; WebKitGTK and related packages on Linux)

Install project dependencies:

```bash
npm run setup
```

Start the complete desktop development stack:

```bash
npm run dev
```

This launches the Tauri window and the development FastAPI service. In development the API is available at:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
```

For browser-only frontend development:

```bash
npm run dev:web
```

Do not start Vite by itself if you expect HydroPilot API-backed actions to work.

## Tests and builds

```bash
npm test
npm run build:web
make verify
```

Create a native Tauri bundle locally:

```bash
npm run build
```

The build first produces a platform-specific PyInstaller FastAPI sidecar and then packages it with Tauri. Packaged applications select a free loopback port automatically; users do not need Python or a manually started backend.

## Runtime architecture

```text
React + CesiumJS
      │
      │ Tauri HTTP / commands
      ▼
Tauri 2 (Rust)
      │
      ├─ OS credential store
      ├─ desktop lifecycle
      └─ PyInstaller FastAPI sidecar
                 │
                 ├─ water-network topology
                 ├─ 0D reservoir model
                 ├─ 1D Muskingum routing
                 └─ LLM provider adapters
```

## GitHub Releases

The Release workflow reads the application version from `apps/studio/package.json`. When a version does not yet have a published Release, GitHub Actions builds native Tauri packages for:

- macOS Apple Silicon
- macOS Intel
- Windows x64
- Linux x64

A failed build leaves the Release as a draft so the same version can be repaired and retried. A Release is published only after all native jobs complete successfully.

## V0.1 / V0.3 model scope

HydroPilot deliberately layers model complexity:

```text
Reservoir     River network       Local floodplain
   0D              1D                   2D
balance  →     Muskingum      →    SFINCS adapter
```

SFINCS remains an isolated/manual regression capability while the interactive desktop demo focuses on the reservoir + directed-network + routing chain.
