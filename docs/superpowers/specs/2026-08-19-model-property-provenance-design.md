# Model Property Provenance Design

## Problem

HydroPilot has removed several hidden numeric multipliers from code, but the Sacramento fixture still contains solver-driving values such as reservoir initial state/capacity and per-reach Muskingum parameters. Today `HydroObject.source` describes the object as a whole, not the origin or trust level of individual properties.

A value moved from Python into JSON is still a hidden assumption if callers cannot tell whether it is authoritative source data, derived data, or a demonstrator modeling assumption.

## Goal

Add typed property-level provenance to `HydroObject` and annotate every solver-driving property in the Sacramento demo fixture without changing any numeric value or simulation behavior.

The first pass is intentionally conservative: values that have not been independently validated/calibrated for operational use are marked as `model_assumption` even when the surrounding object was seeded from a public source.

## Domain model

Add:

`PropertyValueOrigin`

- `source_data`
- `derived`
- `model_assumption`

Add `PropertyProvenance`:

- `origin: PropertyValueOrigin`
- `source: str`
- `note: str | None`

Extend `HydroObject` with:

`property_provenance: dict[str, PropertyProvenance] = {}`

This is additive and backwards compatible for repositories/objects without property-level metadata.

## Solver-driving properties in the demo

For the current release scenario, require provenance for properties that directly affect model state or routing:

Reservoir:

- `initial_storage_m3`
- `max_storage_m3`
- `initial_level_m` when present

River reach:

- `routing_k_minutes`
- `routing_x`

The Sacramento demonstrator marks these current fixture values as `model_assumption` unless/until a future change replaces a value with validated engineering/source data and changes its provenance accordingly.

Routing notes must explicitly say the Muskingum K/X values are uncalibrated demonstrator parameters and are not operational flood-routing parameters.

Reservoir-state/capacity notes must explicitly say the v0.1 fixture values are demonstrator model inputs and require authoritative validation before operational use.

No numeric property value is changed by this PR.

## Validation

Add a reusable fixture provenance check for the solver-driving property set:

- if one of the relevant properties exists, a matching `property_provenance` entry must exist;
- the provenance entry must parse through the typed domain model;
- every demo `routing_k_minutes` / `routing_x` entry must currently be classified `model_assumption`;
- current reservoir scenario-driving values must currently be classified `model_assumption`.

This validation is about transparency, not about asserting the assumption is physically correct.

## API/tool behavior

Because `HydroObject` is returned by the existing object API and `get_object` tool, property provenance becomes visible automatically there.

Compact `list_objects` remains compact and does not add provenance payloads; callers that need detailed properties/provenance use `get_object`.

## Compatibility boundary

Unchanged:

- all numeric fixture values;
- release scenario equations and parameters consumed;
- repository query contracts;
- object geometry;
- Agent allowlist;
- compact object inventory shape.

## Non-goals

- sourcing/calibrating replacement Muskingum parameters;
- claiming current demo values are authoritative;
- adding URLs/citations for values that have not been validated;
- changing scenario outputs;
- enforcing provenance on every arbitrary property in every future repository;
- operational model certification.

## Success criteria

- every current solver-driving demo property has typed property-level provenance;
- current K/X and demo initialization values are transparently labeled modeling assumptions;
- API/get_object exposes the provenance;
- compact list_objects stays unchanged;
- no numeric fixture/model behavior changes;
- repository CI remains green.
