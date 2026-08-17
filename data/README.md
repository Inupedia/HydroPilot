# Data

HydroPilot v0.1 uses public/open hydrology and GIS data for a small Sacramento River Basin demonstrator.

## Repository policy

Large source datasets are **not** committed to Git. Source archives and local caches belong under `data/raw/` or `data/cache/`, both of which are ignored.

Small deterministic fixtures derived from public data may be committed under `data/fixtures/` when they include a `PROVENANCE.md` documenting publisher, source page, retrieval date, selection method, retained fields, and any derived relationships.

Canonical HydroPilot spatial data is stored in EPSG:4326 and model/API interfaces use SI units.

HydroPilot v0.1 is a software demonstrator and its fixtures must not be used for operational flood-control or reservoir-dispatch decisions.
