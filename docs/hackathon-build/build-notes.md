# Build Notes

## 2026-08-29 - Scope and planning baseline

Source: `GDG Cloud&DevOps Round 2.pdf`, Task 1 - LLM Sandbox.

Decisions:

- Treat the LLM prompt boundary as the game surface and the backend/infrastructure boundary as production security infrastructure.
- Use a unique proof token per session so one participant cannot simply share the solution with everyone else.
- Reveal the next-round hint only after server-side verification of the proof token in model output.
- Keep the MVP API-only and use generated interactive API documentation for the demo.
- Favor a stateless Python/FastAPI service plus Redis over a database-heavy or queue-heavy design.
- Support participant-provided credentials without storing them, and reject arbitrary provider URLs.
- Target Docker plus Render for an inexpensive, reproducible cloud path.

Assumptions requiring organizer confirmation before production:

- The event can distribute a round access code out of band.
- A session-specific proof token is acceptable even though the brief refers to a singular solution.
- The organizer will provide the next-round hint and server secret through deployment secrets.
- Raw prompt/response retention is not required for judging.

Interview/deepening rounds: 0. The participant asked for direct creation of the PRD and architecture, so the first draft uses explicit, documented assumptions from the challenge brief and can be revised without changing the core boundaries.

## 2026-08-29 - Product requirements

The PRD expands the brief into six stable epics: entry, credential modes, attempts, solve/reward, boundaries/privacy, and operation/demo. The intentionally surprising cases captured explicitly are duplicate requests after a client disconnect, two concurrent successful responses, session expiry during an in-flight provider call, provider authentication versus sandbox authorization, and shared-state failure after a chargeable model response.

Scope guardrails retained: API-only MVP, single-turn text, approved provider presets, ephemeral storage, no leaderboard, no account system, no arbitrary provider URLs, and no content-retention feature.
