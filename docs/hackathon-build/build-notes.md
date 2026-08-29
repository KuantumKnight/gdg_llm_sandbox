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

## 2026-08-29 - Build item 1 complete

Created the installable Python package, FastAPI factory, Pydantic settings and provider preset contract, environment example, locked dependency graph, Ruff/mypy/pytest configuration, and initial configuration tests. Production validation rejects placeholder secrets, unsafe remote HTTP providers, duplicate presets, and wildcard CORS.

Verified with dependency sync, Ruff, strict mypy, and five passing configuration tests on Python 3.11. Production container target remains Python 3.13; the package intentionally supports Python 3.11-3.13 so the local evaluator can run it.

## 2026-08-29 - Build item 2 complete

Implemented independent session credentials, peppered bearer digests, constant-time secret checks, opaque identifiers, HMAC-bound canonical request digests, session-specific Base32 proof derivation, versioned prompt rendering, exact output-only solve checks, and AES-256-GCM replay encryption bound to session/idempotency associated data.

Verified with Ruff, strict mypy, and thirteen focused security/challenge/crypto tests including tamper rejection and proof isolation. Corrected the development replay key to an exact 32-byte decoded key.

## 2026-08-30 - Initial deployment live

Created the free Render Python service `gdg-llm-sandbox` in the confirmed workspace and Singapore region with auto-deploy from `main`. The first build exposed a runtime mismatch because Render defaulted to Python 3.14 while the project supports 3.11-3.13. Setting `PYTHON_VERSION=3.13.7` fixed the build; the root and interactive docs returned HTTP 200 at `https://gdg-llm-sandbox-637q.onrender.com`.

## 2026-08-30 - Build item 3 complete

Implemented versioned Redis keys, TTL-bound session persistence, token-bucket admission limits, one-call session locks, global preset concurrency, atomic attempt reservation, idempotency conflict/replay states, safe reservation release, ambiguous-outcome recording, and first-writer-wins solve transitions through Lua scripts.

The local Docker CLI exists but its daemon was unavailable. The same Lua scripts were verified with `fakeredis[lua]`; `compose.test.yml` remains available for a real Redis run when Docker is started. Ruff, strict mypy, all prior unit tests, and eight shared-state integration tests pass (26 total).

## 2026-08-30 - Build item 4 complete

Implemented the narrow provider port, fixed OpenAI-compatible Chat Completions adapter, request-scoped participant credential mode, server-managed credential mode, zero SDK retries, fixed model/base URL/roles/temperature/output cap, normalized provider errors with explicit charging semantics, and an operator-only provider registry.

Added a deterministic development stub that refuses ordinary requests and reveals the proof only for documented injection triggers, enabling no-cost automated and live demonstrations. Ruff, strict mypy, and five provider contract/registry tests pass.

## 2026-08-30 - Build item 5 complete

Added versioned public configuration, access-code session creation, one-time bearer return, peppered bearer authorization, solved-session reads, liveness, Redis-aware readiness, stable domain/validation error envelopes, request correlation, request-size enforcement, and optional exact-origin CORS.

The API factory supports an injected repository for deterministic tests while production owns its Redis lifecycle. Ruff, strict mypy, and eight API tests cover safe configuration exposure, generic access denial, unknown presets, forbidden extra fields, missing/wrong/cross-session bearers, authenticated expiry, and health behavior.

## 2026-08-30 - Build item 6 complete

Completed the attempt endpoint and orchestration path: bearer authorization, prompt and UUID idempotency validation, HMAC request binding, atomic reservation, challenge proof/prompt assembly, provider call, explicit charge release versus ambiguous outcome, exact output-only solve detection, atomic solved state, encrypted replay persistence, and next-round hint unlock.

Replay returns the exact prior body without another charge; changing the prompt under the same idempotency key is rejected; participant input containing a proof-like token cannot solve; solved sessions short-circuit before provider work. Ruff, strict mypy, and the full 48-test suite pass.

## 2026-08-30 - Build item 7 complete

Added allowlist-only JSON logs with defense-in-depth secret redaction, request correlation and latency records, low-cardinality Prometheus HTTP/session/attempt/provider metrics, constant-time bearer protection for the scrape endpoint, strict default CORS, API no-store behavior, and browser-facing response security headers.

Security regressions verify that configured secrets stay out of public configuration and OpenAPI, unknown log fields such as prompts are discarded, sentinel credentials are redacted, oversized bodies fail before parsing, and metrics disclose only bounded operational labels. Ruff, strict mypy, seven focused privacy/metrics tests, and the full 55-test suite pass.

## 2026-08-30 - Build item 8 complete

Added an explicit PRD-to-test verification matrix, repository-level 85% coverage enforcement, provider failure/accounting integration tests, and an opt-in test that executes the production Lua transitions against real Redis under a unique self-cleaning namespace. The deterministic stub and mocked provider clients keep the default suite free of paid calls.

The local Docker daemon remains unavailable, so the real-Redis case is skipped locally unless `TEST_REDIS_URL` is supplied; the packaging milestone will run it through the CI Redis service. Ruff, strict mypy, all 57 locally runnable tests, and 91% application coverage pass.

## 2026-08-30 - Build item 9 complete

Added a pinned Python 3.13 multi-stage image with a non-root runtime, minimal build context, Compose API/Redis topology, dependency-free health probe, schema-valid Render Blueprint, tracked-file credential scan, and GitHub Actions quality and container jobs. CI executed the real-Redis Lua test, 85% coverage gate, secret scan, image build, Compose health wait, and in-container readiness smoke successfully.

Provisioned a private free Render Key Value instance in Singapore, wired it to the existing auto-deployed web service, and verified `/health/ready` plus the complete normal-attempt, exact-replay, injection-solve, and hint-reveal flow at `https://gdg-llm-sandbox-637q.onrender.com`. The Blueprint keeps Render's existing immutable Python runtime and locked `uv` environment; Docker provides the equivalent non-root local and CI artifact.

## 2026-08-30 - Build item 10 complete

Replaced the design-phase README with a reviewer-ready quick start, live links, architecture and request flow, API map, security/privacy boundary, failure charging matrix, configuration, verification, deployment, scaling/cost rationale, tradeoffs, and documentation index. Added a production operator guide covering preflight, settings, health, rotation, monitoring, incident response, capacity, and event closeout.

Added credential-safe smoke and deterministic demo CLIs. The live demo command verified readiness, isolated session creation, normal refusal, exact replay without a second charge, injection solve, hint unlock, and solved-session read while keeping the bearer out of output.
