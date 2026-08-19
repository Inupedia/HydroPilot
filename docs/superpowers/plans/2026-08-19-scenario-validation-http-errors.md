# Scenario Validation HTTP Error Implementation Plan

## File structure

- `apps/api/tests/test_api_objects.py` — RED/GREEN HTTP behavior for scenario service validation failures.
- `apps/api/src/hydropilot_api/main.py` — map `ValueError` from scenario execution to HTTP 422.

## Task 1 — RED

Add tests proving:

1. a service `ValueError` becomes HTTP 422 and preserves the message;
2. a missing reservoir remains HTTP 404;
3. a normal request remains HTTP 200.

Expected state: the `ValueError` test fails because the endpoint currently returns an unhandled server error.

## Task 2 — GREEN

Add one explicit `except ValueError` branch after the existing `KeyError` handling in `release_scenario`.

Do not catch `Exception` broadly and do not change service validation logic.

## Task 3 — verification

- inspect the complete diff;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
