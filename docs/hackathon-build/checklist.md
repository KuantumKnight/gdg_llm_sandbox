# Build Checklist

## Build Preferences

- **Build mode:** Autonomous
- **Comprehension checks:** N/A
- **Git:** One commit and push per verified implementation slice
- **Verification:** Yes - automated tests, lint, types, container smoke checks where available
- **Check-in cadence:** Speed-run; progress updates after meaningful slices, no participant review pauses
- **Wow moment:** A normal request is refused, a prompt injection makes the model reveal the session proof, and the same API response unlocks the next-round hint

## Checklist

- [x] **1. Scaffold the typed application and validated configuration**
  Spec ref: `spec.md > 3. Stack; 10. File Structure; 16. CI/CD and Deployment`
  What to build: Create the Python package, locked dependency setup, application factory, settings and preset models, safe environment example, quality-tool configuration, and initial test harness.
  Acceptance: Production settings reject placeholder/weak secrets and unsafe provider configuration; the package imports cleanly and quality tools run from documented commands.
  Verify: `uv sync --all-groups && uv run ruff check . && uv run mypy app`

- [x] **2. Implement challenge, access, and replay-security primitives**
  Spec ref: `spec.md > 6.3 Access and session service; 6.4 Challenge engine; 6.7 Redis repositories and atomic scripts`
  What to build: Add random session credentials, constant-time verification, HMAC proof derivation, prompt rendering, exact output-only solve checks, HMAC request digests, and versioned AES-GCM replay encryption.
  Acceptance: Proofs are deterministic per session and unique across sessions; participant input cannot satisfy verification; tampered replay ciphertext fails closed; no secret value is serialized accidentally.
  Verify: `uv run pytest tests/unit/test_security.py tests/unit/test_challenge.py tests/unit/test_replay_crypto.py`

- [x] **3. Build Redis session, idempotency, quota, and atomic-transition repositories**
  Spec ref: `spec.md > 8. Redis Data Model; 9. End-to-End Data Flow; 13.3 Redis failure points`
  What to build: Add namespaced Redis repositories and Lua scripts for session creation/read, bearer verification data, attempt reservation, locks, token-bucket limits, idempotency pending/completed/unknown states, replay TTL, and first-writer-wins solve state.
  Acceptance: Multiple API replicas share authoritative state; concurrent reservations cannot exceed session limits; duplicate keys never reserve twice; live keys have bounded TTLs and no proof/provider credential is stored.
  Verify: `uv run pytest tests/integration/test_redis_repositories.py`; additionally run `docker compose -f compose.test.yml up -d redis` and the same tests against real Redis when a Docker daemon is available.

- [x] **4. Implement the bounded OpenAI-compatible provider gateway**
  Spec ref: `spec.md > 6.6 Provider gateway; 13.2 Provider retry matrix`
  What to build: Add request/result ports, public preset registry, request-scoped AsyncOpenAI adapter, fixed messages/parameters, output limits, credential modes, total timeout, and normalized upstream errors with explicit charging semantics.
  Acceptance: Participants cannot alter provider URL/model/role/parameters; participant keys are request-scoped; provider bodies/headers never leak; ambiguous failures are not automatically retried.
  Verify: `uv run pytest tests/contract/test_openai_compatible.py tests/unit/test_provider_registry.py`

- [x] **5. Expose configuration, session, and health APIs**
  Spec ref: `spec.md > 7.1 Public configuration; 7.2 Create a session; 7.3 Read a session; 7.5 Health and metrics`
  What to build: Add request IDs, body/content validation, error envelopes, public configuration, round-code admission, session creation/read authorization, liveness, and Redis-aware readiness routes with OpenAPI examples.
  Acceptance: Valid admission returns a bearer once; invalid access is generic and limited; cross-session or expired authorization fails; public endpoints expose no private URL, key, proof, prompt, or hint.
  Verify: `uv run pytest tests/api/test_config.py tests/api/test_sessions.py tests/api/test_health.py`

- [x] **6. Complete attempt orchestration, idempotent replay, solve, and hint reveal**
  Spec ref: `spec.md > 6.5 Attempt orchestrator; 7.4 Submit an attempt; 9.2 Attempt lifecycle; 9.3 Solve lifecycle`
  What to build: Connect validation, authorization, Redis reservation, challenge prompt, provider call, charging policy, exact proof verification, atomic solve, encrypted replay, solved-session short circuit, and stable errors.
  Acceptance: One accepted request creates at most one provider call; replay returns the exact result; wrong-session proofs fail; exact model output solves once and unlocks the hint; no hint is returned before solved state.
  Verify: `uv run pytest tests/api/test_attempts.py tests/integration/test_attempt_concurrency.py`

- [x] **7. Add privacy-safe observability and infrastructure hardening**
  Spec ref: `spec.md > 11. Security Architecture; 14. Observability and Privacy`
  What to build: Add allowlist JSON logs, correlation IDs, low-cardinality metrics, protected metrics access, strict CORS behavior, trusted proxy configuration, response security headers, and sentinel redaction tests.
  Acceptance: Logs, metrics, errors, Redis inspection, and OpenAPI contain no live credentials, access tokens, prompts, proof tokens, system prompts, or hints; health and metrics reveal only intended operational data.
  Verify: `uv run pytest tests/security tests/api/test_metrics.py`

- [x] **8. Finish the automated verification matrix and load-safe test doubles**
  Spec ref: `spec.md > 15. Testing and Verification; 20. Risks and Verification Gates`
  What to build: Complete unit, API, contract, real-Redis integration, race, expiry, charging, malformed-input, SSRF, secret-leak, and deterministic provider-stub tests; enforce coverage and quality gates.
  Acceptance: Every PRD epic has automated evidence; concurrent calls preserve counts and solve state; test runs make no paid provider calls; coverage focuses on security and state transitions.
  Verify: `uv run ruff format --check . && uv run ruff check . && uv run mypy app && uv run pytest --cov=app --cov-report=term-missing --cov-fail-under=85`

- [x] **9. Package, reproduce, deploy, and continuously verify the service**
  Spec ref: `spec.md > 5. Deployment Architecture; 16. CI/CD and Deployment`
  What to build: Add non-root multi-stage Dockerfile, Docker Compose app/Redis stack, Render Blueprint, healthcheck, GitHub Actions CI, `.dockerignore`, and immutable production command.
  Acceptance: A clean clone can start the same image locally; container health/readiness pass; configuration stays external; CI runs lint, types, tests, secret scanning, image build, and smoke checks.
  Verify: `docker compose up -d --build && docker compose ps && docker compose exec -T api python -m app.smoke && docker compose down`

- [x] **10. Complete README, operator guide, and deterministic demo workflow**
  Spec ref: `spec.md > 17. External APIs and Dependency Documentation; 21. Demo and Submission Flow`
  What to build: Expand the README with setup, API examples, data flow, security boundary, access control, edge cases, failure/charging behavior, cost/scaling rationale, encountered problems/mitigations, test commands, deployment steps, and a no-cost demo script.
  Acceptance: A reviewer can reproduce and understand the project from the repository, demonstrate normal/solve/replay behavior in under five minutes, and identify all deliberate security tradeoffs.
  Verify: `uv run python scripts/demo.py --mode stub && uv run python scripts/smoke.py http://localhost:8000`

- [x] **11. Prepare submission handoff**
  Spec ref: `prd.md > Submission Proof Points; spec.md > 21. Demo and Submission Flow`
  What to build: Gather the project story, final architecture and security proof points, public repository link, deployment and demo instructions, test evidence, remaining organizer configuration, and a concise video shot list.
  Acceptance: The repository contains enough verified material to deploy, record the demonstration, and prepare the event submission without reconstructing decisions from chat.
  Verify: Review `README.md`, `docs/hackathon-build/`, final test output, commit history, and remote repository state; confirm remaining external steps are explicitly listed.
