# Storage-Level Curve Wiring Design

## Problem

HydroPilot already has two complementary curve models that are not connected:

- API/domain `HydroCurve` can represent a `level_storage` relationship as level on x and storage on y;
- hydropilot-core `StorageLevelCurve` can derive reservoir level from storage for 0D simulation.

The repository exposes only objects and relations, so release scenarios cannot discover engineering curves. As a result, reservoir level becomes unknown after storage changes even when a future data source provides a valid level-storage curve.

## Goal

Add a repository curve contract and an explicit adapter from domain `HydroCurve` to core `StorageLevelCurve`, then use that curve consistently in reservoir scenario initialization and stepping.

No synthetic Shasta curve is added by this change.

## Design

### Repository contract

Extend `HydroRepository` with:

`list_curves(object_id: str | None = None, curve_type: CurveType | None = None) -> list[HydroCurve]`

The fixture repository reads an optional top-level `curves` array. Existing fixtures without that key remain valid and expose an empty curve list.

### Level-storage convention

For `CurveType.LEVEL_STORAGE`, the domain contract is:

- x = level;
- `x_unit = "m"`;
- y = storage;
- `y_unit = "m3"`.

The scenario adapter reverses each domain point into core `StorageLevelPoint(storage_m3=y, level_m=x)`.

The core validator remains authoritative for monotonic storage and level behavior.

### Curve selection

For a reservoir scenario:

- zero `level_storage` curves: return `None` and preserve current no-curve behavior;
- exactly one curve: validate units and adapt it;
- more than one curve: fail explicitly because the scenario has no version/effective-date selection policy yet.

### Reservoir initialization

When a valid storage-level curve exists, derive the initial reservoir level from `initial_storage_m3` using the curve. Do not trust a separate `initial_level_m` property that could disagree with the engineering relationship.

When no curve exists, preserve the existing optional `initial_level_m` behavior at t=0.

### Reservoir stepping

Pass the adapted `StorageLevelCurve` to every `step_reservoir` call. This makes level states remain available as storage changes, provided storage stays within the curve domain.

Out-of-domain storage is an explicit model/data configuration error; no extrapolation or invented level is allowed.

## Scope

- repository protocol and fixture repository;
- release scenario curve adapter/wiring;
- focused repository/scenario tests.

## Non-goals

- adding Shasta engineering curve values;
- scraping or digitizing USBR charts;
- persistence schema migrations;
- curve versioning/effective dates;
- API curve endpoints;
- level-area or discharge-curve use;
- extrapolation.

## Success criteria

- existing Sacramento fixture loads with zero curves and remains compatible;
- a repository-provided level-storage curve produces initial and subsequent level states;
- wrong units, duplicate curves, or out-of-domain storage fail explicitly;
- no synthetic engineering data is added;
- repository CI remains green.
