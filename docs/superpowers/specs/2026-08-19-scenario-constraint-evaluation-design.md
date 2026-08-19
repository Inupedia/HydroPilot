# Scenario Constraint Evaluation Design

## Problem

HydroPilot can now store and query typed operating constraints, but scenario results do not report whether computed states violate those limits. Simply enforcing every constraint would be unsafe because some semantics are not defined yet: `active_when` conditions have no evaluator, ramp-rate units/time basis are not normalized, and the domain does not yet distinguish hard vs advisory constraints.

## Goal

Add a conservative post-simulation constraint-evaluation layer that reports violations only when comparison semantics are unambiguous, and explicitly reports constraints that were not evaluated.

The scenario remains a demonstrator and does not automatically alter or reject a release schedule because of a violation.

## Design

### Response additions

Extend `ReleaseScenarioResponse` with:

- `violations: list[ConstraintViolation]`
- `unevaluated_constraints: list[UnevaluatedConstraint]`

Both default to empty lists so existing consumers remain compatible.

`ConstraintViolation` records:

- constraint id;
- object id;
- variable;
- timestamp;
- computed value and unit;
- constraint type and configured bounds;
- source/provenance.

`UnevaluatedConstraint` records:

- constraint id;
- object id;
- variable;
- reason.

### Supported evaluation

Evaluate only unconditional constraints (`active_when == {}`) of types:

- `minimum`
- `maximum`
- `range`

For each constraint, match scenario states by the same `object_id` and `variable`.

Comparison rules:

- MINIMUM: violation when value < min_value;
- MAXIMUM: violation when value > max_value;
- RANGE: violation when value < min_value or value > max_value;
- equality at a bound is valid.

### Unit safety

A supported constraint may be compared only when every matching scenario state has exactly the same unit as the constraint. A mismatch is a scenario/model configuration error and raises `ValueError`; the API layer already maps that to HTTP 422.

No automatic unit conversion is introduced in this PR.

### Explicitly unevaluated constraints

Return an `UnevaluatedConstraint` instead of guessing when:

- `active_when` is non-empty;
- `constraint_type` is `ramp_rate`;
- the scenario produces no matching state variable for that object.

This prevents the absence of a violation from being misread as compliance.

### Object coverage

Evaluate constraints for every object that appears in scenario state output, including the reservoir and routed river reaches. This allows the same layer to report reservoir release/storage/level constraints and downstream flow constraints.

### Execution order

1. validate/build model configuration;
2. run reservoir and river simulation;
3. evaluate constraints against completed states;
4. return states + violations + unevaluated constraints.

Constraint evaluation does not mutate states or rerun the model.

## Scope

- scenario response models;
- post-simulation constraint evaluation;
- focused tests;
- compatibility shims for in-memory repositories used by scenario tests.

## Non-goals

- hard/soft constraint semantics;
- blocking or optimizing release schedules;
- `active_when` condition evaluation;
- ramp-rate evaluation;
- unit conversion;
- rule evaluation;
- adding Sacramento operating constraints;
- Studio visualization.

## Success criteria

- unconditional MIN/MAX/RANGE violations are reported deterministically;
- bound equality is not a violation;
- conditional/ramp/missing-variable constraints are explicitly unevaluated;
- unit mismatch returns a configuration error rather than comparing incompatible values;
- Sacramento with zero constraints returns empty evaluation lists;
- existing state results remain unchanged;
- repository CI remains green.
