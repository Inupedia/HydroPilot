# HydroPilot v0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a testable Sacramento-basin water-network digital-twin demonstrator with PostGIS topology, public-data-derived fixtures, a 0D reservoir model, 1D Muskingum routing, Cesium visualization, and an isolated SFINCS smoke/regression workflow.

**Architecture:** Keep deterministic water-model logic in pure Python packages, canonical geometry/topology/scenario state in PostgreSQL/PostGIS, HTTP concerns in FastAPI, and visualization concerns in Vue/Cesium. Geometry and topology are separate first-class concepts. SFINCS sits behind an adapter and is never required for normal PR CI.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL/PostGIS, pytest, Vue 3, TypeScript, Vite, Pinia, CesiumJS, Vitest, Playwright, Docker Compose, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-17-hydropilot-v0.1-design.md`

## Global Constraints

- All canonical spatial geometry is stored in EPSG:4326.
- SI units are mandatory in backend/model interfaces.
- v0.1 must run without an LLM API key.
- No large source dataset is committed to Git.
- Every public-data-derived fixture includes attribution/provenance.
- Core model calculations are deterministic.
- PR CI stays lightweight; full-basin or expensive 2D simulation is prohibited in required PR checks.
- The product must state that v0.1 is a demonstrator, not an operational flood-control or dispatch decision system.
- New behavior is developed test-first where practical.
- Each implementation task must produce independently testable software.

---

## File structure locked for v0.1

```text
HydroPilot/
├── apps/
│   ├── api/
│   │   ├── pyproject.toml
│   │   ├── alembic.ini
│   │   ├── alembic/
│   │   ├── src/hydropilot_api/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── db.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── routes/
│   │   │   │   ├── objects.py
│   │   │   │   ├── network.py
│   │   │   │   └── scenarios.py
│   │   │   └── services/
│   │   │       ├── network.py
│   │   │       └── scenarios.py
│   │   └── tests/
│   └── web/
│       ├── package.json
│       ├── vite.config.ts
│       ├── src/
│       │   ├── main.ts
│       │   ├── App.vue
│       │   ├── api/
│       │   ├── components/
│       │   ├── cesium/
│       │   ├── stores/
│       │   └── types/
│       └── tests/
├── packages/
│   ├── hydro-core/
│   │   ├── pyproject.toml
│   │   ├── src/hydropilot_core/
│   │   │   ├── reservoir.py
│   │   │   ├── muskingum.py
│   │   │   └── types.py
│   │   └── tests/
│   └── hydro-data/
│       ├── pyproject.toml
│       ├── src/hydropilot_data/
│       │   ├── dto.py
│       │   ├── hydrorivers.py
│       │   ├── usgs.py
│       │   ├── nid.py
│       │   └── fixture.py
│       └── tests/
├── data/
│   ├── fixtures/sacramento-demo/
│   │   ├── objects.geojson
│   │   ├── relations.json
│   │   ├── gauges.json
│   │   └── PROVENANCE.md
│   └── README.md
├── infra/sfincs/tiny/
├── scripts/
│   ├── import_demo.py
│   └── check_demo.py
├── .github/workflows/
│   ├── ci.yml
│   └── sfincs-regression.yml
├── docker-compose.yml
├── Makefile
└── README.md
```

---

### Task 1: Bootstrap API, local PostGIS, and repository developer commands

**Files:**
- Create: `.gitignore`
- Create: `Makefile`
- Create: `docker-compose.yml`
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/src/hydropilot_api/__init__.py`
- Create: `apps/api/src/hydropilot_api/main.py`
- Create: `apps/api/src/hydropilot_api/config.py`
- Create: `apps/api/tests/test_health.py`
- Create: `data/README.md`

**Interfaces:**
- Produces: `hydropilot_api.main.app: FastAPI`
- Produces: `GET /health -> {"status": "ok", "service": "hydropilot-api"}`
- Produces: environment variable `DATABASE_URL`, defaulting locally to `postgresql+psycopg://hydropilot:hydropilot@localhost:5432/hydropilot`

- [ ] **Step 1: Write the failing API health test**

```python
from fastapi.testclient import TestClient
from hydropilot_api.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "hydropilot-api",
    }
```

- [ ] **Step 2: Run the test and verify the package does not exist yet**

Run:

```bash
cd apps/api
python -m pytest tests/test_health.py -v
```

Expected: FAIL because `hydropilot_api` has not been created.

- [ ] **Step 3: Add the minimal FastAPI application**

```python
from fastapi import FastAPI

app = FastAPI(title="HydroPilot API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "hydropilot-api"}
```

- [ ] **Step 4: Add local PostGIS Compose service**

Use a Compose service named `db` with database/user/password `hydropilot`, host port `5432`, a healthcheck using `pg_isready`, and a named volume `hydropilot_pgdata`. Use a PostGIS image compatible with PostgreSQL 16.

Verify syntax:

```bash
docker compose config
```

Expected: exit code 0.

- [ ] **Step 5: Add developer commands**

The `Makefile` must expose:

```text
make db-up
make db-down
make api-test
make api-dev
```

`make api-test` runs `pytest`; `make api-dev` runs Uvicorn on port `8000`.

- [ ] **Step 6: Run the health test**

```bash
cd apps/api
python -m pytest tests/test_health.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add .gitignore Makefile docker-compose.yml apps/api data/README.md
git commit -m "feat: bootstrap api and postgis development environment"
```

---

### Task 2: Create canonical PostGIS domain schema and directed network traversal

**Files:**
- Create: `apps/api/alembic.ini`
- Create: `apps/api/alembic/env.py`
- Create: `apps/api/alembic/versions/0001_hydro_domain.py`
- Create: `apps/api/src/hydropilot_api/db.py`
- Create: `apps/api/src/hydropilot_api/models.py`
- Create: `apps/api/src/hydropilot_api/schemas.py`
- Create: `apps/api/src/hydropilot_api/services/network.py`
- Create: `apps/api/tests/integration/test_schema.py`
- Create: `apps/api/tests/integration/test_network.py`

**Interfaces:**
- Produces SQL tables: `hydro_object`, `hydro_relation`, `scenario`, `hydro_state`
- Produces: `get_downstream_path(session, object_id: UUID, max_hops: int) -> list[NetworkHop]`
- `NetworkHop` fields: `object_id: UUID`, `hop: int`

- [ ] **Step 1: Write a failing migration/schema integration test**

The test connects to `DATABASE_URL`, applies migrations, then asserts:

```python
assert {"hydro_object", "hydro_relation", "scenario", "hydro_state"} <= table_names
```

It must additionally execute:

```sql
SELECT PostGIS_Version();
```

and assert a non-empty result.

- [ ] **Step 2: Start PostGIS and verify the schema test fails**

```bash
docker compose up -d db
cd apps/api
python -m pytest tests/integration/test_schema.py -v
```

Expected: FAIL because migrations/tables do not exist.

- [ ] **Step 3: Implement the first Alembic migration**

Create enums and tables from the design spec. The `hydro_object.geometry` column must use SRID 4326 and a GiST index named:

```text
ix_hydro_object_geometry_gist
```

Create indexes on:

```text
hydro_object(object_type)
hydro_object(source, external_id)
hydro_relation(source_id, relation_type)
hydro_relation(target_id, relation_type)
hydro_state(scenario_id, timestamp)
```

- [ ] **Step 4: Write a failing downstream traversal test**

Insert this topology:

```text
A -> B -> C -> D
     \
      -> X
```

where all arrows are `FLOWS_TO`. Assert `get_downstream_path(A, max_hops=2)` returns `A@0`, `B@1`, then `C@2` and `X@2` in deterministic UUID/string order.

- [ ] **Step 5: Implement recursive traversal**

Use a PostgreSQL recursive CTE over `hydro_relation` restricted to `relation_type = 'FLOWS_TO'`. Track visited IDs in the recursive state so a malformed cycle cannot loop indefinitely.

Function contract:

```python
@dataclass(frozen=True)
class NetworkHop:
    object_id: UUID
    hop: int


def get_downstream_path(
    session: Session,
    object_id: UUID,
    max_hops: int,
) -> list[NetworkHop]: ...
```

Reject `max_hops < 0` and cap values above `100` to prevent accidental unbounded API queries.

- [ ] **Step 6: Run integration tests**

```bash
cd apps/api
python -m pytest tests/integration/test_schema.py tests/integration/test_network.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/api/alembic.ini apps/api/alembic apps/api/src/hydropilot_api apps/api/tests/integration
git commit -m "feat: add hydro domain schema and network traversal"
```

---

### Task 3: Build public-data normalization and deterministic Sacramento demo fixture

**Files:**
- Create: `packages/hydro-data/pyproject.toml`
- Create: `packages/hydro-data/src/hydropilot_data/__init__.py`
- Create: `packages/hydro-data/src/hydropilot_data/dto.py`
- Create: `packages/hydro-data/src/hydropilot_data/hydrorivers.py`
- Create: `packages/hydro-data/src/hydropilot_data/usgs.py`
- Create: `packages/hydro-data/src/hydropilot_data/nid.py`
- Create: `packages/hydro-data/src/hydropilot_data/fixture.py`
- Create: `packages/hydro-data/tests/test_hydrorivers.py`
- Create: `packages/hydro-data/tests/test_fixture.py`
- Create: `data/fixtures/sacramento-demo/objects.geojson`
- Create: `data/fixtures/sacramento-demo/relations.json`
- Create: `data/fixtures/sacramento-demo/gauges.json`
- Create: `data/fixtures/sacramento-demo/PROVENANCE.md`
- Create: `scripts/import_demo.py`
- Create: `scripts/check_demo.py`

**Interfaces:**
- Produces: `HydroObjectDTO`
- Produces: `HydroRelationDTO`
- Produces: `normalize_hydrorivers_record(record) -> tuple[HydroObjectDTO, HydroRelationDTO | None]`
- Produces: `load_demo_fixture(path: Path) -> DemoFixture`

DTOs must include source and provenance metadata; geometry is GeoJSON-like mapping in EPSG:4326 before persistence.

- [ ] **Step 1: Write failing HydroRIVERS normalization tests**

Use a tiny in-memory record containing `HYRIV_ID=101`, `NEXT_DOWN=102`, a LineString, and representative attributes. Assert:

```python
obj.external_id == "101"
obj.object_type == "river_reach"
obj.source == "HydroRIVERS"
relation.source_external_id == "101"
relation.target_external_id == "102"
relation.relation_type == "FLOWS_TO"
relation.provenance_method == "source_connectivity"
```

- [ ] **Step 2: Implement DTOs and HydroRIVERS normalization**

No database dependency is allowed in this package. Normalizers accept plain mappings and return typed DTOs.

- [ ] **Step 3: Produce a small public-data-derived demo fixture**

Use official HydroRIVERS North/Central America data as the river-topology source, clipped to a deliberately small Sacramento demo extent so the committed fixture remains small. Add selected USGS gauge metadata and a small number of USACE NID dam records only when provenance can be retained.

The committed fixture target is intentionally bounded:

```text
river reaches: 20-200
dams/engineering objects: 1-20
gauges/control points: 2-20
```

Do not commit continental source archives.

- [ ] **Step 4: Document fixture provenance**

`PROVENANCE.md` must include, for every source:

```text
source name
publisher
source product/API page
retrieval date
license/terms reference
selection/clipping method
fields retained
derived-relation method
```

It must state that the fixture is for software demonstration/testing and not operational decision support.

- [ ] **Step 5: Write and run fixture validation tests**

Tests must assert:

```python
assert len(fixture.objects) >= 20
assert any(o.object_type == "river_reach" for o in fixture.objects)
assert any(r.relation_type == "FLOWS_TO" for r in fixture.relations)
assert all(o.crs == "EPSG:4326" for o in fixture.objects)
assert fixture.external_ids_are_unique()
assert fixture.relations_reference_existing_or_declared_objects()
```

- [ ] **Step 6: Implement idempotent import script**

`scripts/import_demo.py` uses `(source, external_id)` identity and upserts canonical objects/relations. Running it twice must leave row counts unchanged.

- [ ] **Step 7: Verify import idempotency against PostGIS**

```bash
python scripts/import_demo.py
python scripts/check_demo.py --write-counts /tmp/counts-1.json
python scripts/import_demo.py
python scripts/check_demo.py --compare-counts /tmp/counts-1.json
```

Expected: PASS with unchanged object/relation counts.

- [ ] **Step 8: Commit**

```bash
git add packages/hydro-data data/fixtures scripts/import_demo.py scripts/check_demo.py
git commit -m "feat: add public water-network data pipeline and demo fixture"
```

---

### Task 4: Implement deterministic 0D reservoir mass-balance model

**Files:**
- Create: `packages/hydro-core/pyproject.toml`
- Create: `packages/hydro-core/src/hydropilot_core/__init__.py`
- Create: `packages/hydro-core/src/hydropilot_core/types.py`
- Create: `packages/hydro-core/src/hydropilot_core/reservoir.py`
- Create: `packages/hydro-core/tests/test_reservoir.py`

**Interfaces:**
- Produces: `ReservoirState(storage_m3: float)`
- Produces: `ReservoirStep(inflow_m3s: float, release_m3s: float, dt_seconds: float)`
- Produces: `advance_reservoir(state: ReservoirState, step: ReservoirStep) -> ReservoirState`

- [ ] **Step 1: Write failing mass-balance tests**

```python
def test_reservoir_mass_balance() -> None:
    state = ReservoirState(storage_m3=1_000_000.0)
    next_state = advance_reservoir(
        state,
        ReservoirStep(inflow_m3s=100.0, release_m3s=50.0, dt_seconds=3600.0),
    )
    assert next_state.storage_m3 == pytest.approx(1_180_000.0)
```

Also test that storage floors at zero and `dt_seconds <= 0` raises `ValueError`.

- [ ] **Step 2: Run tests and verify failure**

```bash
cd packages/hydro-core
python -m pytest tests/test_reservoir.py -v
```

Expected: FAIL because implementation does not exist.

- [ ] **Step 3: Implement the smallest deterministic model**

```python
def advance_reservoir(state: ReservoirState, step: ReservoirStep) -> ReservoirState:
    if step.dt_seconds <= 0:
        raise ValueError("dt_seconds must be positive")
    next_storage = state.storage_m3 + (
        step.inflow_m3s - step.release_m3s
    ) * step.dt_seconds
    return ReservoirState(storage_m3=max(0.0, next_storage))
```

Validate negative flow inputs according to the DTO contract: v0.1 rejects negative inflow/release rather than assigning reverse-flow semantics.

- [ ] **Step 4: Run tests**

```bash
cd packages/hydro-core
python -m pytest tests/test_reservoir.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/hydro-core
git commit -m "feat: add reservoir mass balance model"
```

---

### Task 5: Implement 1D Muskingum reach routing and regression fixture

**Files:**
- Create: `packages/hydro-core/src/hydropilot_core/muskingum.py`
- Create: `packages/hydro-core/tests/test_muskingum.py`
- Create: `packages/hydro-core/tests/fixtures/muskingum_reference.json`

**Interfaces:**
- Produces: `MuskingumReach(k_seconds: float, x: float, dt_seconds: float)`
- Produces: `route_muskingum(inflows_m3s: Sequence[float], initial_outflow_m3s: float, reach: MuskingumReach) -> list[float]`

- [ ] **Step 1: Write failing parameter validation tests**

Assert that the model rejects:

```text
K <= 0
X < 0
X > 0.5
dt <= 0
unstable coefficient combinations
```

Use an error message that names the invalid parameter.

- [ ] **Step 2: Write a failing hydrograph regression test**

Use this compact inflow hydrograph:

```python
inflows = [10, 10, 20, 50, 100, 50, 20, 10, 10]
```

The checked regression properties are:

```python
assert len(outflows) == len(inflows)
assert max(outflows) < max(inflows)
assert outflows.index(max(outflows)) >= inflows.index(max(inflows))
assert all(q >= 0 for q in outflows)
```

Once the first implementation is independently checked against a hand calculation/reference notebook, store exact expected values in `muskingum_reference.json` and compare with `pytest.approx` at a documented tolerance.

- [ ] **Step 3: Implement standard Muskingum coefficients**

Use:

```text
C0 = (dt - 2*K*X) / (2*K*(1-X) + dt)
C1 = (dt + 2*K*X) / (2*K*(1-X) + dt)
C2 = (2*K*(1-X) - dt) / (2*K*(1-X) + dt)
O[t+1] = C0*I[t+1] + C1*I[t] + C2*O[t]
```

Reject coefficient sets that produce a negative coefficient for the supported v0.1 configuration rather than silently routing an unstable setup.

- [ ] **Step 4: Run model tests**

```bash
cd packages/hydro-core
python -m pytest tests/test_muskingum.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/hydro-core/src/hydropilot_core/muskingum.py packages/hydro-core/tests
git commit -m "feat: add muskingum river routing"
```

---

### Task 6: Expose objects, topology, and release-routing scenarios through FastAPI

**Files:**
- Create: `apps/api/src/hydropilot_api/routes/__init__.py`
- Create: `apps/api/src/hydropilot_api/routes/objects.py`
- Create: `apps/api/src/hydropilot_api/routes/network.py`
- Create: `apps/api/src/hydropilot_api/routes/scenarios.py`
- Create: `apps/api/src/hydropilot_api/services/scenarios.py`
- Modify: `apps/api/src/hydropilot_api/main.py`
- Modify: `apps/api/src/hydropilot_api/schemas.py`
- Create: `apps/api/tests/integration/test_objects_api.py`
- Create: `apps/api/tests/integration/test_network_api.py`
- Create: `apps/api/tests/integration/test_scenario_api.py`

**Interfaces:**
- Produces endpoints listed in the design spec.
- `POST /api/scenarios/release-routing` consumes `ReleaseRoutingRequest`.
- `ReleaseRoutingRequest` fields: `name`, `start_time`, `dt_seconds`, `initial_storage_m3`, `inflows_m3s`, `releases_m3s`, `reach_ids`.

- [ ] **Step 1: Write failing object GeoJSON API test**

Seed one LineString `river_reach`. Call:

```text
GET /api/objects?types=river_reach
```

Assert `FeatureCollection`, SRID-normalized coordinates, object ID, name, type, and source are present.

- [ ] **Step 2: Implement object listing and object detail routes**

Bounding-box filtering uses PostGIS geometry operators, not Python-side filtering.

- [ ] **Step 3: Write failing downstream API test**

Call:

```text
GET /api/network/{id}/downstream?max_hops=3
```

Assert the JSON response includes each object and its `hop`.

- [ ] **Step 4: Wire the recursive network service into routes**

Return HTTP 404 for an unknown start object and HTTP 422 for invalid `max_hops`.

- [ ] **Step 5: Write failing release-routing scenario test**

Submit a two-reach scenario with deterministic inputs. Assert:

```python
assert response.status_code == 201
assert body["scenario"]["scenario_type"] == "simulation"
assert len(body["states"]) > 0
assert body["states"][0]["storage_m3"] is not None
assert any(s["flow_m3s"] is not None for s in body["states"])
```

- [ ] **Step 6: Implement scenario service**

The service calls only `hydropilot_core` for calculations, then persists `scenario` and `hydro_state` rows in one transaction. If any input reach is missing or is not connected in the requested order, reject the request before inserting scenario state.

- [ ] **Step 7: Run API integration suite**

```bash
cd apps/api
python -m pytest tests/integration -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add apps/api/src/hydropilot_api apps/api/tests/integration
git commit -m "feat: expose water network and routing scenario api"
```

---

### Task 7: Build Vue/Cesium map-first water-network viewer

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/vite.config.ts`
- Create: `apps/web/index.html`
- Create: `apps/web/src/main.ts`
- Create: `apps/web/src/App.vue`
- Create: `apps/web/src/api/client.ts`
- Create: `apps/web/src/types/hydro.ts`
- Create: `apps/web/src/stores/network.ts`
- Create: `apps/web/src/cesium/viewer.ts`
- Create: `apps/web/src/cesium/renderNetwork.ts`
- Create: `apps/web/src/components/NetworkPanel.vue`
- Create: `apps/web/src/components/ObjectDetail.vue`
- Create: `apps/web/tests/renderNetwork.test.ts`

**Interfaces:**
- Consumes: `GET /api/objects`
- Consumes: `GET /api/network/{id}/downstream`
- Produces: `renderHydroFeatures(viewer, featureCollection) -> RenderedHydroLayer`
- Produces: `highlightObjectPath(viewer, objectIds: string[]) -> void`

- [ ] **Step 1: Write failing renderer classification unit test**

Given GeoJSON features with types `river_reach`, `dam`, and `gauge`, assert the rendering adapter classifies them into line/engineering/point render specifications without creating a real WebGL viewer in the unit test.

- [ ] **Step 2: Implement Cesium-independent render-spec conversion**

Keep semantic style decisions in a pure function:

```ts
type HydroRenderSpec =
  | { kind: 'flow-line'; objectId: string; coordinates: number[][] }
  | { kind: 'engineering-point'; objectId: string; position: number[] }
  | { kind: 'gauge-point'; objectId: string; position: number[] }
```

Cesium object creation consumes these specs in a separate function.

- [ ] **Step 3: Bootstrap Vue/Vite/Cesium**

Create a full-height map-first shell with a narrow left network panel. Configure Cesium static assets through Vite so local production build works without CDN-only assumptions.

- [ ] **Step 4: Load canonical objects from API and render them**

On initial load, fetch the demo bounding box/type set and render lines/points. Selecting a feature updates the Pinia selected-object state.

- [ ] **Step 5: Implement downstream path highlighting**

When the user selects `Highlight downstream`, fetch the downstream API and visually distinguish every returned object. The styling must be reversible without reloading the dataset.

- [ ] **Step 6: Run frontend tests and build**

```bash
cd apps/web
pnpm test
pnpm build
```

Expected: PASS and successful Vite build.

- [ ] **Step 7: Commit**

```bash
git add apps/web
git commit -m "feat: add cesium water network viewer"
```

---

### Task 8: Add release-scenario controls and timeline-driven scene state

**Files:**
- Create: `apps/web/src/stores/scenario.ts`
- Create: `apps/web/src/components/ScenarioPanel.vue`
- Create: `apps/web/src/components/ScenarioTimeline.vue`
- Create: `apps/web/src/cesium/applyScenarioState.ts`
- Create: `apps/web/tests/scenarioStore.test.ts`
- Create: `apps/web/tests/applyScenarioState.test.ts`
- Modify: `apps/web/src/App.vue`
- Modify: `apps/web/src/api/client.ts`

**Interfaces:**
- Consumes: `POST /api/scenarios/release-routing`
- Consumes: `GET /api/scenarios/{id}/states?timestamp=`
- Produces: `scenarioStore.currentTimestamp`
- Produces: `applyScenarioState(renderedLayer, states) -> void`

- [ ] **Step 1: Write failing scenario-store tests**

Test that loading a scenario creates a sorted timestamp list, clamps timeline index to valid bounds, and exposes the current timestamp deterministically.

- [ ] **Step 2: Implement scenario store and API calls**

The store contains scenario metadata and state snapshots; Cesium objects themselves never live in Pinia.

- [ ] **Step 3: Write failing scene-state mapping test**

Given two state rows with different `flow_m3s`, assert `applyScenarioState` produces deterministic visual-state values while preserving the selected/downstream highlight semantic layer.

- [ ] **Step 4: Implement scenario panel and timeline**

The default demo form exposes only defensible inputs:

```text
scenario name
release hydrograph preset
start button
```

Advanced hydraulic controls are not shown in v0.1.

- [ ] **Step 5: Add one Playwright smoke flow**

Test:

```text
open app
wait for Cesium shell
load fixture-backed network
select an object
run a demo release scenario
move timeline to a later timestep
assert displayed timestamp changes
```

Mock only external terrain/network services; keep HydroPilot API live in the E2E job.

- [ ] **Step 6: Run tests**

```bash
cd apps/web
pnpm test
pnpm build
pnpm playwright test
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/web
git commit -m "feat: add routing scenario timeline visualization"
```

---

### Task 9: Make GitHub Actions the v0.1 quality gate

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `Makefile`
- Modify: `README.md`

**Interfaces:**
- Produces required jobs: `backend-unit`, `hydro-core`, `postgis-integration`, `frontend`, `e2e-smoke`
- No paid API secret is required.

- [ ] **Step 1: Add a local aggregate verification command**

`make verify` runs the same logical checks as CI except browser installation/setup details:

```text
backend unit tests
hydro-core tests
hydro-data tests
frontend unit tests
frontend build
```

- [ ] **Step 2: Create `ci.yml` with PostGIS service for integration tests**

The integration job must:

```text
start PostGIS
wait for health
apply Alembic migrations
import demo fixture
run API integration tests
run idempotency check
```

- [ ] **Step 3: Add frontend and Playwright jobs**

Cache pnpm dependencies. Build before browser smoke testing. Use the API against a PostGIS test service rather than mocking HydroPilot HTTP responses end-to-end.

- [ ] **Step 4: Run workflow syntax checks locally where available**

At minimum run:

```bash
docker compose config
make verify
```

Expected: PASS.

- [ ] **Step 5: Push the task branch and confirm all required Actions jobs pass**

If a job fails, use the failing job logs to fix the root cause before moving on. Do not mark the task complete on partial green status.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/ci.yml Makefile README.md
git commit -m "ci: add hydropilot v0.1 quality gate"
```

---

### Task 10: Add isolated SFINCS tiny-model adapter and scheduled/manual regression

**Files:**
- Create: `packages/hydro-core/src/hydropilot_core/flood.py`
- Create: `packages/hydro-core/src/hydropilot_core/sfincs.py`
- Create: `packages/hydro-core/tests/test_sfincs_adapter.py`
- Create: `infra/sfincs/tiny/` fixture files required by the selected verified SFINCS release
- Create: `infra/sfincs/tiny/expected_metrics.json`
- Create: `scripts/run_sfincs_regression.py`
- Create: `.github/workflows/sfincs-regression.yml`
- Modify: `README.md`

**Interfaces:**
- Produces protocol/interface `FloodModelAdapter.run(run_dir: Path) -> FloodRunResult`
- `FloodRunResult` fields: `exit_code`, `log_path`, `metrics_path`
- Produces CLI exit code 0 only when solver run and metric comparison both pass.

- [ ] **Step 1: Write failing adapter command-construction test**

Test that the Docker adapter constructs a command equivalent to:

```text
docker run --rm -v <absolute-run-dir>:/data <pinned-sfincs-image>
```

The unit test must not invoke Docker.

- [ ] **Step 2: Select and pin a verified SFINCS Docker release**

Use a tagged official `deltares/sfincs-cpu` release that successfully runs the committed tiny fixture on the standard GitHub-hosted Ubuntu runner. Record the exact image tag in the workflow and README; do not use mutable `latest` in regression CI.

- [ ] **Step 3: Create the tiny solver fixture**

The fixture must be intentionally small enough for a hosted CI run and contain no large DEM. Keep the simulated period short and the grid coarse. Commit only the model input files required to reproduce the regression.

- [ ] **Step 4: Define regression metrics rather than binary-file equality**

`run_sfincs_regression.py` extracts and compares at least:

```text
solver exit code
maximum water depth
number or area of wet cells
```

Store tolerances alongside expected values in `expected_metrics.json`.

- [ ] **Step 5: Create a non-blocking workflow**

Triggers:

```yaml
workflow_dispatch:
schedule:
  - cron: '23 9 * * 1'
```

The workflow runs the SFINCS Docker image, executes metric comparison, and uploads solver log plus metrics JSON as artifacts. It is not added to the required PR gate.

- [ ] **Step 6: Verify one hosted workflow run**

Expected: solver exits 0, metrics pass tolerance, artifacts are downloadable.

If the standard hosted runner cannot run the verified image/fixture, document the exact incompatibility and change only this workflow to a compatible self-hosted runner label; keep PR CI unaffected.

- [ ] **Step 7: Commit**

```bash
git add packages/hydro-core/src/hydropilot_core/flood.py packages/hydro-core/src/hydropilot_core/sfincs.py packages/hydro-core/tests/test_sfincs_adapter.py infra/sfincs scripts/run_sfincs_regression.py .github/workflows/sfincs-regression.yml README.md
git commit -m "feat: add sfincs tiny flood regression adapter"
```

---

### Task 11: Final v0.1 documentation and release verification

**Files:**
- Create: `docs/architecture/v0.1.md`
- Modify: `README.md`
- Modify: `data/README.md`

**Interfaces:**
- Documentation must match actual startup/test commands and actual API paths.

- [ ] **Step 1: Write architecture documentation from the implemented system**

Document this flow using the names that exist in code:

```text
public fixture -> normalization -> PostGIS object/topology
                                  |
user scenario -> reservoir -> Muskingum -> hydro_state
                                  |
                               FastAPI
                                  |
                             Vue + Cesium
```

Document SFINCS as an isolated flood-model adapter, not as the normal release-routing engine.

- [ ] **Step 2: Update README quickstart**

A fresh developer must be able to follow commands equivalent to:

```bash
docker compose up -d db
make db-migrate
make demo-import
make api-dev
make web-dev
```

Then separately:

```bash
make verify
```

Do not publish commands that have not been executed successfully.

- [ ] **Step 3: Verify the acceptance criteria manually**

Check every acceptance criterion in the design spec and record any deviation in the release PR. No criterion may be silently skipped.

- [ ] **Step 4: Run final verification**

```bash
make verify
docker compose config
```

Then confirm required GitHub Actions are green on the release candidate commit.

- [ ] **Step 5: Commit**

```bash
git add README.md data/README.md docs/architecture/v0.1.md
git commit -m "docs: finalize hydropilot v0.1 architecture and quickstart"
```

---

## Self-review performed

### Spec coverage

- Public data/provenance: Task 3.
- Explicit water-network topology: Tasks 2-3.
- PostGIS canonical storage: Tasks 1-3.
- 0D reservoir: Task 4.
- 1D routing: Task 5.
- Scenario persistence/API: Task 6.
- Cesium water-network display: Task 7.
- Timeline/state display: Task 8.
- Required GitHub Actions: Task 9.
- SFINCS isolated regression: Task 10.
- Documentation/limitations: Task 11.

### Placeholder scan

No implementation task relies on `TBD`, an unnamed handler, or an undefined neighboring interface. The only intentionally deferred choice is the exact SFINCS verified release tag; Task 10 makes selecting and validating that external runtime the explicit first integration action before the fixture/workflow is accepted.

### Type consistency

The implementation uses these stable boundaries throughout:

```text
HydroObjectDTO / HydroRelationDTO -> PostGIS domain
ReservoirState + ReservoirStep -> deterministic reservoir state
MuskingumReach + inflow sequence -> routed outflow sequence
NetworkHop -> topology API
scenario + hydro_state -> frontend scenario store
HydroRenderSpec -> Cesium renderer
FloodModelAdapter -> optional SFINCS runner
```

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-17-hydropilot-v0.1.md`.

Recommended execution mode: **superpowers:subagent-driven-development**, one task at a time, with review gates between tasks. `superpowers:executing-plans` is the fallback for inline/batched execution.
