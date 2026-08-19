# List Objects Hydro Tool Implementation Plan

## File structure

- `apps/api/src/hydropilot_api/tools.py` — args model, handler, registry entry.
- `apps/api/src/hydropilot_api/agent.py` — explicit Agent allowlist expansion.
- `apps/api/tests/test_tools.py` — registry execution/filter validation.
- `apps/api/tests/test_tools_api.py` — real demo API execution coverage.
- `apps/api/tests/test_agent.py` — Agent advertised-tool regression.

## Task 1 — RED

Prove:

1. catalog order includes `list_objects`;
2. test repository can list all objects;
3. `object_type=river_reach` returns only reaches;
4. invalid object type fails validation;
5. real demo `/api/tools/execute` can list reservoir objects;
6. Agent advertises exactly the new five-tool allowlist and still excludes scenario/write tools.

## Task 2 — GREEN

- add `ListObjectsArgs` with optional `ObjectType`;
- add `_list_objects` delegating directly to `repo.list_objects(...)`;
- register the tool with a read-only inventory description;
- add `list_objects` to the explicit Agent allowlist.

Do not add a dedicated HTTP endpoint or change repository behavior.

## Task 3 — verification

- inspect diff for unintended Agent capability expansion;
- require repository CI to pass;
- squash merge;
- verify merged branch deletion.
