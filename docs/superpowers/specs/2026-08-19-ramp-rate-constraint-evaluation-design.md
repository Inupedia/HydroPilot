# Ramp-Rate Constraint Evaluation Design

## Problem

HydroPilot now evaluates unconditional minimum, maximum, and range constraints after a release scenario, while every `ramp_rate` constraint is reported as unevaluated. The scenario output already contains ordered time-series states, so a narrow ramp-rate interpretation can be implemented without changing simulation behavior.

The unsafe part is unit/time semantics. A `ramp_rate` record only carries `unit` and `max_value`; it does not separately encode the base variable unit, time basis, asymmetric up/down limits, or conditional activation.

## Goal

Evaluate only ramp-rate constraints whose unit has one exact, auditable meaning relative to the matching scenario state:

`<scenario state unit>/h`

For example, a `release` state measured in `m3/s` may be evaluated against a ramp-rate constraint measured in `m3/s/h`.

All other ramp-rate unit forms remain explicitly unevaluated rather than converted or guessed.

## Design

### Supported semantics

For an unconditional `ConstraintType.RAMP_RATE` constraint:

1. find scenario states matching the same `object_id` and `variable`;
2. sort by `timestamp_minutes`;
3. require at least two matching states;
4. require all matching states to share one state unit;
5. require the constraint unit to equal `<state.unit>/h` exactly;
6. for each adjacent state pair compute:

`rate = abs(next.value - current.value) / ((next.timestamp_minutes - current.timestamp_minutes) / 60)`

7. report a violation when `rate > max_value`;
8. equality to `max_value` is valid;
9. attribute a violation to the later timestamp in the pair.

The absolute value means the current domain's single `max_value` is interpreted as the maximum magnitude of change, regardless of increase or decrease. Asymmetric ramp-up/ramp-down semantics remain out of scope.

### Violation representation

Reuse `ConstraintViolation`:

- `value` is the computed ramp magnitude per hour;
- `unit` is the ramp-rate constraint unit;
- `constraint_type` is `ramp_rate`;
- `max_value` is the configured ramp limit;
- timestamp is the later state in the adjacent pair.

### Explicitly unevaluated cases

A ramp-rate constraint remains unevaluated when:

- `active_when` is non-empty;
- fewer than two matching scenario states exist;
- matching state timestamps cannot form a positive interval;
- the ramp-rate unit is not exactly `<state.unit>/h`.

No automatic unit/time conversion is introduced.

If matching states themselves contain inconsistent units, raise `ValueError` because the scenario output is internally inconsistent.

### Execution boundary

Ramp-rate evaluation remains post-simulation and advisory. It does not alter the release schedule, rerun routing, or block scenario execution because of a violation.

## Non-goals

- minute/day ramp units;
- unit conversion such as cfs to m3/s;
- asymmetric ramp-up/ramp-down limits;
- conditional `active_when` evaluation;
- dispatch optimization or enforcement;
- adding Sacramento operating constraints.

## Success criteria

- supported `<state-unit>/h` ramp constraints produce deterministic violations;
- equality at the ramp limit passes;
- decreasing values are checked by magnitude;
- unsupported ramp units are explicitly unevaluated;
- conditional ramp constraints remain unevaluated;
- simulation states remain unchanged;
- repository CI remains green.
