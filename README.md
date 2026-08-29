# GDG LLM Sandbox

`gdg_llm_sandbox` is a backend for a prompt-injection challenge at a GDG VIT Chennai TechnoVIT event. Participants send prompts to an LLM and try to make it reveal a session-specific proof token hidden in the system prompt. A successful reveal unlocks the hint for the next round.

The project is currently in the design phase. The implementation will prioritize a well-designed, reproducible core over feature breadth.

## Planning documents

- [Product scope](docs/hackathon-build/scope.md)
- [Product requirements](docs/hackathon-build/prd.md)
- [Technical specification and architecture](docs/hackathon-build/spec.md)
- [Planning decisions](docs/hackathon-build/build-notes.md)

## Design goals

- Intentionally breakable at the LLM prompt boundary, but secure at the infrastructure boundary.
- Compatible with a server-funded LLM, a participant-provided API key, or an approved self-hosted OpenAI-compatible endpoint.
- Stateless API instances with ephemeral shared state for horizontal scaling.
- Strict cost controls through quotas, output caps, timeouts, concurrency limits, and idempotency.
- No logging or durable persistence of participant API keys, raw prompts, hidden proof tokens, or model responses; completed responses may exist briefly in an encrypted idempotency cache for safe replay.
- Docker-first local and cloud reproduction.

## Status

Planning only. API code, tests, deployment configuration, and the demonstration workflow will be implemented from the technical specification.
