# Studio Scenario Constraint Results Implementation Plan

## File structure

- `apps/studio/src/api/client.ts` — typed full release-scenario response.
- `apps/studio/src/scenario/evaluation.ts` — pure summary/format helpers.
- `apps/studio/src/scenario/evaluation.css` — compact result styles.
- `apps/studio/src/App.tsx` — retain and render backend evaluation results.
- `apps/studio/tests/scenarioEvaluation.test.ts` — RED/GREEN formatting and compliance wording.
- `apps/studio/tests/scenarioApi.test.ts` — RED/GREEN full scenario API response preservation.

## Task 1 — RED client/helper tests

Prove:

1. `hydroApi.releaseScenario()` returns states, violations, and unevaluated constraints from the backend response;
2. violation summaries include object, variable, timestamp, value/unit, and applicable bound;
3. minimum/maximum/range/ramp-rate result types format deterministically;
4. unevaluated summaries include object, variable, and reason;
5. the compliance disclaimer explicitly says zero violations does not imply operational compliance.

## Task 2 — GREEN client/helper

- define typed violation/unevaluated/release response interfaces;
- return the full scenario response from the client;
- add pure deterministic formatting helpers and disclaimer constant.

## Task 3 — GREEN App integration

- add violation and unevaluated state;
- on successful run, replace states + both evaluation collections from one response;
- include counts in the scenario-ready action message;
- render compact counts and up to three detail rows;
- show overflow counts and the compliance disclaimer;
- keep scenario execution button explicit and unchanged.

## Task 4 — styling

- add an isolated compact evaluation stylesheet;
- do not modify backend behavior or the existing compressed main stylesheet.

## Task 5 — verification

- inspect diff to confirm Agent/scenario execution logic is unchanged;
- require React tests/build and repository CI to pass;
- squash merge;
- verify merged branch deletion.
