# HydroPilot

HydroPilot is a water-network digital twin demonstrator for flood-control and dispatch scenes.

V0.1 proves the foundation: public water-network data, directed topology, simple deterministic hydro models, APIs, and a Cesium map-first UI. The current desktop track packages the same Cesium experience as a self-contained Electron application.

## What HydroPilot includes

- Sacramento public-data-derived demo fixture.
- `hydro_object` / `hydro_relation` domain model.
- Directed downstream traversal over `FLOWS_TO` relations.
- 0D reservoir mass balance.
- 1D Muskingum river routing.
- FastAPI object, topology, and release-scenario APIs.
- Vue 3 + Cesium water-network viewer.
- Timeline-driven scenario state.
- Electron desktop shell with local API sidecar management.
- Desktop-local same-origin proxy so the renderer does not depend on a fixed API port.
- GitHub Actions quality gates and packaged Electron Cesium smoke testing.
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
```

Web app:

```bash
cd apps/web
npm install
npm run dev
```

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

The `Desktop` GitHub Actions workflow also supports manual cross-platform packaging for macOS, Windows, and Linux. Its Linux acceptance job launches the packaged Electron binary under Chromium/Xvfb and only passes after a real Cesium canvas and all 24 demo objects are visible.

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

Only small, reviewable demo fixtures are committed. Raw public datasets, model outputs, and generated caches stay out of Git.

## Safety and scope

HydroPilot remains a demonstrator. It is not operational flood-control, reservoir-dispatch, emergency warning, or engineering-design decision support.
