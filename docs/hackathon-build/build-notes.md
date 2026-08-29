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

Architecture self-review finding: exact idempotent replay and a blanket ban on retaining model output were contradictory. The privacy contract now permits only an encrypted completed-response replay record with a maximum ten-minute TTL. It remains forbidden to retain prompts, credentials, system prompts, proof tokens, or conversation history.

## 2026-08-29 - Technical specification and architecture

Stack: Python 3.13, FastAPI/Uvicorn, Pydantic Settings, OpenAI-compatible async provider client, Redis/Valkey, AES-GCM replay encryption, Prometheus metrics, pytest, Docker Compose, Render, and GitHub Actions.

Architecture decisions: stateless API replicas; Redis-only ephemeral state; API-only interactive demo; fixed provider presets; no queue or relational database; exact output-only proof verification; required idempotency; one in-flight attempt per session; separate secrets for admission, proof derivation, request digests, replay encryption, observability, hint, and providers.

Architecture self-review findings surfaced for organizer confirmation:

1. A session-specific proof reduces sharing but may differ from an expected single global answer. The API supports either choice without route changes.
2. Ambiguous provider timeouts must remain charged to prevent silent duplicate cost; this tradeoff is visible to participants.
3. Returning the current configured hint to old solved sessions is simple, but hint rotation during the event would require a `hint_version` snapshot for consistency.

Research was limited to current official documentation for FastAPI containers, Pydantic settings, OpenAI-compatible provider surfaces (OpenAI, Gemini, Ollama, vLLM), async redis-py, AES-GCM, and Render deployment.

## 2026-08-29 - Build checklist

Build mode locked to autonomous with automated verification and no participant review pauses. Git cadence is one commit and push per verified implementation slice. The participant's direct instruction to "build the app" is treated as confirmation to execute the checklist immediately.

The submission wow moment is the exact core loop already established in the PRD: normal refusal, successful session-specific proof extraction, automatic solve verification, and immediate hint reveal. Checklist review found eleven appropriately sequenced slices; shared state and provider-contract risks are built before the public attempt workflow.
