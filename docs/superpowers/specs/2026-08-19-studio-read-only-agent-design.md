# Studio Read-Only Agent Integration Design

## Problem

Studio's Copilot currently classifies free text with frontend regular expressions. A downstream phrase directly triggers map highlighting, and a release/flow phrase plus a number directly runs a release scenario. Only unmatched prompts use the generic LLM chat endpoint.

HydroPilot now has a backend read-only Agent with typed repository tools and a strict API boundary. Keeping the regex command path would leave two conflicting Agent models: the backend is read-only, while frontend text can still execute scenario actions.

## Goal

Make free-text Copilot strictly read-only and backend-Agent-driven.

- free-text questions -> `POST /api/agent/chat`;
- network highlighting -> explicit UI button only;
- release scenario execution -> explicit UI button only.

## Studio API client

Add typed Agent request/response contracts and `hydroApi.agentChat()`.

The Studio request does not include `tools` or system messages.

## Provider selection

The current Agent supports only `openai-compatible` providers. Studio therefore exposes only provider catalog entries with `adapter_family === "openai-compatible"` in the Copilot provider selector.

A previously stored unsupported provider id is replaced at startup by the first compatible provider.

## Agent conversation context

The backend Agent owns the trusted system prompt. Studio sends only `user`/`assistant` messages.

Before each new question, Studio appends one user message containing a concise read-only snapshot of UI state:

- object/reach/asset counts;
- current scenario timeline minute;
- manual inflow and release control values;
- current visible routed peak flow when available;
- an explicit statement that scenario controls are UI-only and unavailable to the Agent.

This context is descriptive. It does not grant execution capability.

## Copilot UX

Change the panel framing from action execution to inquiry:

- heading: "Ask the water network";
- quick prompts ask about downstream topology, engineering objects, curves, and constraints;
- initial message explains that scenario controls remain explicit buttons;
- helper text states that Copilot uses read-only Agent tools.

No free-text phrase is locally interpreted as a command.

## Cleanup

Remove the obsolete regex command parser and its tests. Replace them with tests for:

- Agent-compatible provider filtering;
- construction of user/assistant-only Agent messages;
- API client posting to `/api/agent/chat` without a tools field.

## Non-goals

- allowing Agent-triggered scenario execution;
- allowing Agent-triggered map mutation;
- write tools;
- streaming;
- rendering the tool trace in the UI;
- supporting Anthropic/Gemini/Ollama tool calling in Studio.

## Success criteria

- `parseCopilotCommand` is no longer used or present;
- free text calls `/api/agent/chat`, not `/api/llm/chat`;
- provider selector contains only OpenAI-compatible providers;
- Agent messages contain no system/tool role;
- quick prompts are read-only questions;
- explicit topology/scenario buttons continue working unchanged;
- React tests/build and repository CI remain green.
