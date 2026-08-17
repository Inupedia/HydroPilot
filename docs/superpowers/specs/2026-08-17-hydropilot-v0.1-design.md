# HydroPilot v0.1 Design Specification

## Status

- Version target: `v0.1.0`
- Date: 2026-08-17
- Phase: foundation / demonstrator
- Primary goal: establish a trustworthy water-network digital-twin display foundation that can later support flood-control and reservoir-dispatch workflows.

## Product statement

HydroPilot is an open-source water-network digital twin. It combines public hydrology/GIS data, explicit upstream/downstream topology, lightweight hydrologic/hydraulic models, and Cesium-based 3D visualization.

Version 0.1 is intentionally **not** an operational flood forecasting or dispatch decision system. It is a reproducible technical demonstrator whose data model, interfaces, and tests are designed so later versions can add more advanced forecasting, optimization, and LLM-driven scene planning without replacing the foundation.

## v0.1 user story

A user opens a Sacramento River Basin demo and can:

1. See the river network, major dams/reservoir-related engineering objects, and selected gauges on a Cesium 3D terrain scene.
2. Select a water-network object and inspect its metadata and direct upstream/downstream relationships.
3. Highlight the downstream path from a selected reach/reservoir-related node to a control/gauge point.
4. Run a lightweight release scenario where a reservoir release hydrograph is routed downstream through a simplified river network.
5. Scrub a scenario timeline and see flow/state values update on the map.
6. Run a tiny SFINCS flood-model smoke/regression workflow manually or nightly in GitHub Actions and retain its result as an artifact.

## Explicit non-goals

v0.1 does **not** provide:

- operational flood forecasts;
- automatic reservoir optimization;
- multi-reservoir optimization algorithms;
- production-grade 1D/2D coupling;
- calibration against observed flood events;
- LLM natural-language GIS control;
- automatic model selection/orchestration;
- a complete Sacramento Basin engineering inventory;
- claims that nearest-spatial-object inference represents legal/operational hydraulic connectivity.

## Demo geography and public data

The initial showcase is a **Sacramento River Basin demo subset**, not a promise of complete basin coverage.

Preferred public/open sources:

- **HydroRIVERS / HydroSHEDS**: river reaches and explicit downstream connectivity fields for the network backbone.
- **USACE National Inventory of Dams (NID)**: dam/engineering-object metadata where usable.
- **USGS Water Data APIs**: selected gauge/station metadata and observations.
- **USGS 3DEP or another openly usable terrain source**: terrain context for the Cesium scene.
- Optional later overlay: NOAA/NWPS status data, provided separately from the core v0.1 acceptance criteria.

Every imported object must retain source/provenance metadata. Derived relations must state how they were inferred.

## Core design principle: geometry is not topology

A river is not represented only as a `LineString`. HydroPilot stores both:

- **geometry**: where the object is, in PostGIS;
- **topology**: how water-network objects relate, via explicit directed relations.

For example:

```text
Reach A --FLOWS_TO--> Reach B --FLOWS_TO--> Reach C
                              |
                              +--MONITORED_BY--> Gauge X
```

This explicit network is the foundation for future flood-control and dispatch reasoning.

## Domain model

### `hydro_object`

Canonical water-network object table.

Required fields:

- `id: UUID`
- `external_id: str | null`
- `name: str | null`
- `object_type: enum`
- `geometry: geometry(Geometry, 4326)`
- `properties: JSONB`
- `source: str`
- `source_url: str | null`
- `source_updated_at: timestamptz | null`
- `created_at: timestamptz`

Initial object types:

- `river_reach`
- `dam`
- `reservoir`
- `gauge`
- `control_point`

### `hydro_relation`

Directed semantic relation table.

Required fields:

- `id: UUID`
- `source_id: UUID`
- `target_id: UUID`
- `relation_type: enum`
- `properties: JSONB`
- `provenance_method: str`
- `created_at: timestamptz`

Initial relation types:

- `FLOWS_TO`
- `UPSTREAM_OF`
- `DOWNSTREAM_OF`
- `LOCATED_ON`
- `MONITORED_BY`
- `CONTROLS`
- `DISCHARGES_TO`

`FLOWS_TO` is authoritative when imported from a source that exposes network connectivity. Inverse relations may be derived at query time; they do not need duplicate storage unless profiling later proves it necessary.

### `scenario`

- `id: UUID`
- `name: str`
- `scenario_type: enum(current, historical, simulation)`
- `start_time: timestamptz`
- `end_time: timestamptz`
- `time_step_seconds: int`
- `parameters: JSONB`
- `created_at: timestamptz`

### `hydro_state`

Time-varying state attached to a HydroPilot object.

- `scenario_id: UUID`
- `object_id: UUID`
- `timestamp: timestamptz`
- `flow_m3s: float | null`
- `water_level_m: float | null`
- `storage_m3: float | null`
- `release_m3s: float | null`
- `properties: JSONB`

Primary key/uniqueness: `(scenario_id, object_id, timestamp)`.

## Lightweight model layer

### 0D reservoir model

Purpose: demonstrate storage/release state transitions without pretending to be a full reservoir operations model.

Mass balance:

```text
S(t + dt) = S(t) + (Qin(t) - Qout(t)) * dt
```

Rules:

- SI units only: seconds, cubic metres, cubic metres per second.
- Storage may not become negative.
- Invalid negative timestep raises a validation error.
- Optional storage-to-water-level curve is deferred; v0.1 may expose storage ratio instead of inferred elevation if no defensible curve is available.

### 1D Muskingum routing

Purpose: route a release/inflow hydrograph through simplified river reaches and demonstrate attenuation/travel delay.

Each reach has explicit routing parameters `K_seconds` and dimensionless `X`.

Constraints:

- `K_seconds > 0`;
- `0 <= X <= 0.5`;
- timestep must satisfy the implementation's stability constraints;
- routing preserves mass within a documented numerical tolerance for the regression fixture.

This is a routing model, not a full Saint-Venant hydraulic solver.

### SFINCS adapter

Purpose: prove that HydroPilot can invoke a real open-source 2D flood model through a stable adapter boundary.

v0.1 requirements:

- define a `FloodModelAdapter` interface;
- provide a SFINCS Docker runner for a tiny committed fixture;
- use `deltares/sfincs-cpu` with a pinned verified release tag in CI once the implementation task validates the selected tag;
- run as `workflow_dispatch` and scheduled/nightly, not a required PR check;
- publish solver logs and compact regression metrics as GitHub Actions artifacts;
- no full-basin 2D model is required.

## Backend architecture

Technology:

- Python 3.12+
- FastAPI
- Pydantic v2
- SQLAlchemy 2
- Alembic
- PostgreSQL + PostGIS
- GeoAlchemy2 or equivalent thin spatial mapping
- pytest

Responsibilities:

```text
apps/api/
  HTTP/API boundary
packages/hydro-core/
  pure deterministic reservoir/routing logic
packages/hydro-data/
  source adapters/import/normalization
PostGIS
  canonical spatial objects, relations, scenarios, states
```

Hydrologic model code must not depend on FastAPI or Cesium.

## API surface for v0.1

Minimum endpoints:

- `GET /health`
- `GET /api/objects?bbox=&types=`
- `GET /api/objects/{id}`
- `GET /api/network/{id}/downstream?max_hops=`
- `GET /api/network/{id}/upstream?max_hops=`
- `POST /api/scenarios/release-routing`
- `GET /api/scenarios/{id}`
- `GET /api/scenarios/{id}/states?timestamp=`

Spatial/list responses used by Cesium should be GeoJSON-compatible where practical.

## Frontend architecture

Technology:

- Vue 3
- TypeScript
- Vite
- Pinia
- CesiumJS
- Vitest
- Playwright for one thin end-to-end smoke path

v0.1 layout:

```text
+-------------------------------------------------------------+
| HydroPilot                         Scenario / current time   |
+------------------+------------------------------------------+
| Water Network    |                                          |
| layers           |              Cesium scene                |
| selected object  |                                          |
| relations        |                                          |
| scenario panel   |                                          |
+------------------+------------------------------------------+
| timeline                                                    |
+-------------------------------------------------------------+
```

The UI is map-first. There is no chat/LLM panel in v0.1.

### Visualization semantics

- river reaches: directed flow appearance; selected downstream path visually distinct;
- dams/reservoir objects: distinct engineering symbol/entity;
- gauges/control points: point symbols with state labels on demand;
- scenario state: line width/intensity or compact labels may reflect routed flow;
- no visual encoding may imply calibrated hazard severity unless the source/model actually provides it.

## Public-data normalization

Source adapters transform source-native records into canonical import DTOs before database insertion.

Each adapter must:

1. fetch/read source data;
2. normalize IDs/names/geometry/properties;
3. keep source provenance;
4. validate CRS and convert to EPSG:4326 for canonical storage;
5. be idempotent for the same source snapshot;
6. avoid committing large raw public datasets to Git.

A small, license-compatible deterministic fixture derived from public data may be committed for tests/demo bootstrap, with attribution and provenance documented.

## GitHub Actions strategy

Required PR checks:

- frontend lint/typecheck/unit tests/build;
- backend lint/typecheck/unit tests;
- reservoir and Muskingum regression tests;
- PostGIS integration tests with migrations and tiny fixture;
- API smoke test.

Non-blocking scheduled/manual checks:

- SFINCS tiny-model smoke/regression;
- optional live public-data adapter contract smoke tests.

CI must not require paid LLM APIs or private infrastructure.

## Test strategy

### Unit

- reservoir mass balance and validation;
- Muskingum coefficients/routing and validation;
- source normalization functions;
- frontend state/renderer helpers.

### Integration

- PostGIS migrations apply cleanly;
- GiST geometry index exists;
- downstream recursive traversal returns deterministic ordered/hop-aware results;
- GeoJSON API response contains valid geometries;
- scenario persistence round-trip.

### Regression

Committed tiny fixtures have expected metrics with tolerances, for example:

- mass-balance error tolerance;
- peak routed flow tolerance;
- peak timing tolerance;
- SFINCS maximum depth/flooded-cell metrics when the SFINCS fixture lands.

Regression tests compare engineering metrics, not entire binary output files byte-for-byte.

## Repository structure

```text
HydroPilot/
├── apps/
│   ├── api/
│   └── web/
├── packages/
│   ├── hydro-core/
│   └── hydro-data/
├── data/
│   ├── fixtures/
│   └── README.md
├── docs/
│   ├── architecture/
│   └── superpowers/
│       ├── specs/
│       └── plans/
├── infra/
│   └── sfincs/
├── scripts/
├── .github/workflows/
├── docker-compose.yml
└── README.md
```

## Global constraints

1. All canonical spatial geometry is stored in EPSG:4326.
2. SI units are mandatory in backend/model interfaces.
3. v0.1 must run without an LLM API key.
4. No large source dataset is committed to Git.
5. Every public-data-derived fixture includes attribution/provenance.
6. Core model calculations are deterministic.
7. PR CI stays lightweight; full-basin or expensive 2D simulation is prohibited in required PR checks.
8. The product must state that v0.1 is a demonstrator, not an operational flood-control or dispatch decision system.
9. New behavior is developed test-first where practical.
10. Each implementation task must produce independently testable software.

## v0.1 acceptance criteria

v0.1 is complete when all of the following are true:

1. `docker compose up` provides PostGIS plus runnable API/web development services or clearly documented equivalent commands.
2. A committed small public-data-derived Sacramento demo fixture loads into PostGIS.
3. The Cesium scene renders river reaches, at least one engineering object, and gauges/control points from the API.
4. Selecting an object can highlight a multi-hop downstream path from stored topology.
5. A release-routing scenario persists and returns deterministic time-series states using the 0D reservoir + 1D Muskingum model path.
6. The frontend timeline can render at least two scenario timesteps and update visible state.
7. Required GitHub Actions checks pass on the repository's standard runner.
8. A manual/nightly SFINCS tiny smoke workflow can run independently and publish artifacts; if this external integration proves incompatible with standard hosted runners, the adapter and fixture remain in v0.1 while the workflow is explicitly documented as requiring a compatible runner.
9. README documents architecture, data provenance, local startup, limitations, and testing.
