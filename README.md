# HydroPilot

**AI-native water network digital twin for flood control and reservoir dispatch.**

HydroPilot is an open-source project for building an interactive water-network digital twin from public data. The first milestone focuses on a trustworthy, testable foundation: water-network objects and topology, Cesium-based 3D visualization, simple reservoir and river-routing models, and lightweight flood-model integration.

## v0.1 direction

- Public/open hydrology and GIS datasets
- PostgreSQL + PostGIS water-network data model
- Vue 3 + TypeScript + CesiumJS frontend
- FastAPI backend
- 0D reservoir mass-balance model
- 1D Muskingum river routing
- Optional tiny SFINCS integration/regression fixture
- GitHub Actions for linting, tests, integration tests, and model regression

The v0.1 scope intentionally prioritizes **display, topology, reproducibility, and automated testing** over production-grade flood forecasting or operational dispatch optimization.

## Development approach

Planning and implementation follow the task-oriented workflow inspired by [obra/superpowers](https://github.com/obra/superpowers): design first, bite-sized implementation plans, TDD where practical, frequent commits, and verification before completion.

See `docs/superpowers/` as planning documents are added.
