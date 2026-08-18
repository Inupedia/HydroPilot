# Hydro Domain Foundation Design

## Problem

HydroPilot's current domain model can represent only a small demonstration graph: river reaches, reservoirs, dams, gauges, and control points. That vocabulary is too narrow for flood-control and dispatch workflows because important conveyance, control, diversion, generation, protection, and service objects cannot be expressed explicitly. Curves, operating constraints, and dispatch rules are also stored only as untyped properties, which prevents model adapters and future agents from discovering and validating them consistently.

## Goal

Introduce a small, typed semantic foundation for HydroPilot v0.4 without changing persistence, APIs, model execution, or the desktop UI.

The domain layer should be able to describe:

- physical water-network assets beyond the current five object types;
- directed operational relationships between those assets;
- engineering curves such as level-storage and level-discharge curves;
- numeric operating constraints;
- machine-readable operating rules.

## Scope

This change is intentionally limited to `apps/api/src/hydropilot_api/domain.py` and domain-level tests.

### Object vocabulary

Add object types needed by near-term flood-control and dispatch scenarios:

- channel
- tunnel
- aqueduct
- siphon
- pump station
- gate
- diversion
- intake
- powerhouse
- spillway
- outlet
- flood storage area
- levee
- water-use unit
- irrigation district
- control section

Existing object types remain unchanged for backward compatibility.

### Relationship vocabulary

Add relationships for conveyance, diversion, regulation, service, and administrative grouping while preserving existing relationships.

### Engineering curves

Add a generic `HydroCurve` with typed curve kind, units, and ordered `(x, y)` points. Curves must contain at least two points and x-values must be strictly increasing. This keeps interpolation/model selection out of the domain layer while ensuring usable engineering data.

### Constraints

Add a `HydroConstraint` for minimum, maximum, range, and ramp-rate constraints. Validation should reject structurally invalid bounds (for example a range whose minimum is greater than its maximum).

### Rules

Add a lightweight `HydroRule` carrying priority plus machine-readable condition/action payloads. Rule evaluation is explicitly out of scope.

## Non-goals

- PostgreSQL/PostGIS migrations or repositories
- model-engine changes
- dispatch optimization
- LLM tool calling or agent orchestration
- Cesium/UI changes
- curve interpolation or rule evaluation

## Compatibility

Existing fixture data and existing API endpoints must continue to parse and serialize without changes. New structures are additive.

## Success criteria

- existing domain/API tests remain valid;
- new vocabulary can instantiate typed `HydroObject` and `HydroRelation` values;
- malformed engineering curves and constraints are rejected by validation;
- no production subsystem outside the domain module needs modification.
