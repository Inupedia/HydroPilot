# Studio Agent Grounding Trace Design

## Problem

The backend read-only Agent already returns an ordered `tool_executions` audit trace for every answer, including tool call id, tool name, arguments, and result. Studio currently displays only the final assistant text and discards that trace.

That makes grounded answers visually indistinguishable from text-only answers, even though the backend can prove which repository tools were used.

## Goal

Show a compact grounding trace beneath each assistant answer while keeping conversation payloads clean and read-only.

## Display model

Studio keeps display-only metadata on assistant messages:

- `toolExecutions`: ordered Agent tool executions;
- `providerRounds`: number of provider rounds used.

The visible trace shows:

- label `Grounded by`;
- one compact item per tool execution;
- tool name;
- concise deterministic argument summary.

Examples:

- `list_objects · object_type=reservoir`
- `get_object · object_id=reservoir-shasta`
- `trace_downstream · object_id=reach-001, max_hops=8`

A text-only answer with zero tool executions does not show a grounding trace.

The tool result itself is not rendered in this PR. Results may be large, contain geometry, or duplicate the natural-language answer. The backend response remains available for future inspectable-detail UI.

## Conversation boundary

Display metadata must never be sent back to `/api/agent/chat`.

`buildReadOnlyAgentMessages()` therefore normalizes conversation history to fresh `{role, content}` objects before appending current Studio context. It must not spread or serialize display-only properties.

This is both a cleanliness and safety boundary: backend request history remains limited to the documented Agent message contract.

## Formatting

Add a pure helper for deterministic argument summaries:

- sort argument keys;
- render primitives directly;
- render arrays/objects as compact JSON;
- no argument values -> show only tool name;
- truncate long serialized values to keep the trace compact.

## UX

Grounding trace is visually subordinate to the assistant answer:

- small muted label;
- compact chips/rows;
- readable in the existing Copilot thread;
- no new modal or expandable data inspector.

## Scope

- Studio display message type;
- history normalization;
- grounding summary helper;
- render Agent audit trace under assistant messages;
- focused tests and small styling additions.

## Non-goals

- rendering full tool results;
- backend changes;
- tool execution changes;
- citations/source URLs;
- persisted chat history;
- tool replay;
- write tools or scenario tools.

## Success criteria

- an Agent response with tool executions renders a grounding trace;
- execution ordering is preserved;
- arguments are deterministic and compact;
- text-only responses show no false grounding badge;
- display metadata is stripped before subsequent Agent requests;
- repository CI remains green.
