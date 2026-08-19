# Studio Scenario Constraint Results Design

## Problem

The backend release scenario already returns:

- computed `states`;
- `violations` for constraints that were evaluated and exceeded;
- `unevaluated_constraints` for configured constraints that could not be evaluated safely.

Studio's API client currently discards both evaluation collections and returns only `states`. The user therefore cannot see the result of the backend constraint layer, and an empty visual warning surface can be misread as compliance.

## Goal

Preserve and display the backend scenario constraint evaluation in Studio without changing scenario execution or constraint semantics.

## Studio API contract

Add typed client models for:

`ConstraintViolation`

- constraint id
- object id
- variable
- timestamp
- computed value/unit
- constraint type
- min/max bounds
- source

`UnevaluatedConstraint`

- constraint id
- object id
- variable
- reason

`ReleaseScenarioResponse`

- `scenario_id`
- `states`
- `violations`
- `unevaluated_constraints`

`hydroApi.releaseScenario()` returns this complete response instead of only the state array.

## App state

Studio stores the most recent:

- scenario states;
- violations;
- unevaluated constraints.

Every successful scenario run replaces all three collections together so evaluation metadata can never remain stale from a previous run.

A failed API call leaves the previous successful result visible, matching current state behavior; the action status clearly reports the failure.

## Status message

A successful run reports both model completion and constraint evaluation counts:

`Scenario ready: <N> time steps · <V> violations · <U> unevaluated constraints.`

This remains a successful simulation even when violations exist. A violation is not treated as an HTTP/model execution failure and does not alter the release schedule.

## Constraint result UI

Add a compact section under the scenario result card:

- `Violations` count;
- `Unevaluated` count;
- up to three violation summaries;
- up to three unevaluated summaries;
- overflow count when more items exist.

Violation summary format is deterministic and concise, for example:

`reach-001 · flow · t=60 min · 82 m3/s > max 80 m3/s`

Unevaluated summary:

`reservoir-shasta · release · conditional constraints are not evaluated`

## Compliance wording

Always show a small disclaimer once a scenario result exists:

`Constraint counts cover only configured constraints that HydroPilot can evaluate. Zero violations does not imply operational compliance.`

This avoids turning absence of configured demo constraints into a false safety claim.

## Styling

Use a small isolated stylesheet for the evaluation block instead of expanding the existing compressed main stylesheet.

Violations may use a warning/error accent; unevaluated items use a neutral/warning accent. No modal is added.

## Scope

- Studio API response typing;
- scenario evaluation formatting helpers;
- App storage/rendering of backend evaluation results;
- compact styles/tests.

## Non-goals

- changing backend constraint evaluation;
- blocking scenario execution on violations;
- automatic dispatch correction;
- evaluating additional constraint types;
- adding demo constraints;
- claiming operational compliance;
- Agent-triggered scenario execution.

## Success criteria

- Studio no longer discards `violations` or `unevaluated_constraints`;
- every successful run replaces states + evaluation atomically;
- counts and deterministic summaries render from backend data;
- zero-result wording does not imply compliance;
- existing explicit scenario button behavior remains unchanged;
- React tests/build and repository CI remain green.
