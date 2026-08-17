# Sacramento v0.1 Demo Fixture Provenance

This fixture is a compact, reviewable public-data-derived subset for HydroPilot v0.1.

- River reaches model the directed `NEXT_DOWN -> FLOWS_TO` concept used by HydroRIVERS-style datasets.
- Dam/reservoir objects are shaped after public USACE National Inventory of Dams fields.
- Gauge objects are shaped after public USGS water-data station concepts.

The committed fixture is intentionally small and synthetic-derived for deterministic testing. It preserves public-data semantics without committing raw continental source archives.
