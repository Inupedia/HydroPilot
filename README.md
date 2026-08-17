# HydroPilot

HydroPilot is a water-network digital twin demonstrator for flood-control and dispatch scenes.

V0.1 proves the foundation: public water-network data, directed topology, simple deterministic hydro models, APIs, and a Cesium-ready map-first UI.

## What v0.1 includes

- Sacramento public-data-derived demo fixture.
- `hydro_object` / `hydro_relation` domain model.
- Directed downstream traversal over `FLOWS_TO` relations.
- 0D reservoir mass balance.
- 1D Muskingum river routing.
- FastAPI object, topology, and release-scenario APIs.
- Vue 3 map-first water-network viewer.
- Timeline-driven scenario state.
- GitHub Actions quality gates.
- Optional non-blocking SFINCS tiny regression adapter.

## Quickstart

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

## Data policy

Only small, reviewable demo fixtures are committed. Raw public datasets, model outputs, and generated caches stay out of Git.

## Safety and scope

HydroPilot v0.1 is a demonstrator. It is not operational flood-control, reservoir-dispatch, emergency warning, or engineering-design decision support.
