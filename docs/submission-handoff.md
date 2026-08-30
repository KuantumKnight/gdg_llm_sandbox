# Submission Handoff (Unofficial Draft)

This packet is local project material only. No Devpost event has been registered in this workspace, official form requirements have not been loaded, and nothing has been sent to Devpost.

## Title

GDG LLM Sandbox

## One-line summary

A production-minded prompt-injection challenge where participants attack an LLM's instructions while session isolation, provider access, quotas, idempotency, and secrets remain protected.

## Problem

Prompt-injection exercises often collapse the challenge and its infrastructure into one unsafe surface. A shared flag is easy to copy, arbitrary provider settings create SSRF and credential risks, retries can duplicate paid model calls, and raw prompt logging can expose participant or organizer secrets.

## Solution

GDG LLM Sandbox gives every participant an ephemeral authenticated session and derives a unique hidden proof inside a versioned system prompt. Participants submit single-turn prompts through a bounded provider preset. Redis Lua transitions atomically reserve attempts, rate and concurrency capacity, session locks, idempotency state, replay, and first-solve state. The server checks only model output for the exact proof and reveals the next-round hint after a verified solve.

## Why it matters

The experience teaches the real distinction between an intentionally vulnerable AI instruction boundary and infrastructure that still needs normal production controls. It is inexpensive enough for a student event, reproducible locally, horizontally scalable, and explicit about provider cost and ambiguous failures.

## How AI is used

- The participant-facing challenge is an LLM instruction-following boundary: the system prompt tells the model to protect a session proof, while participant prompts attempt to override it.
- A fixed OpenAI-compatible adapter supports approved hosted or self-hosted models without exposing model, URL, role, temperature, or output-cap controls to participants.
- A deterministic provider reproduces refusal and solve behavior for free CI and judging demos; it makes no claim to model realism and is disabled in production mode.
- The backend—not another model—performs deterministic proof verification, authorization, quota, and reward decisions.

## How Codex was used

Codex translated the challenge brief into a scope, PRD, technical architecture, and 11-item build checklist; reconciled encrypted idempotent replay with the privacy requirement; implemented each verified slice; wrote security, contract, concurrency, provider-failure, and real-Redis tests; created Docker, Compose, CI, and Render configuration; diagnosed the Python runtime mismatch; provisioned managed Redis; and verified the live normal/replay/solve flow. Each logical slice was committed and pushed separately for an auditable history.

## Key features that work today

- Safe public configuration and round-code admission.
- Per-session opaque bearer and HMAC-derived Base32 proof.
- Fixed server-managed or participant-provided provider credential modes.
- Atomic quotas, token buckets, session lock, global preset concurrency, idempotency, and first solve.
- Exact AES-256-GCM replay without a second provider charge.
- Explicit nonchargeable versus ambiguous-chargeable provider failure behavior.
- Output-only solve verification and immediate hint unlock.
- Allowlist JSON logs, protected low-cardinality metrics, response security headers, strict CORS.
- Non-root Docker image, Compose topology, schema-valid Render Blueprint, and required GitHub Actions gates.
- Responsive participant interface with generated editorial imagery and full dark/light themes.
- Live Gemini 3.5 Flash-Lite challenge backed by private Render Key Value.

## Architecture summary

Participant traffic enters a stateless FastAPI service through Render's edge. The API owns validation, session authorization, the challenge engine, and the bounded provider gateway. Redis/Valkey is the only shared state and stores short-lived sessions, digests, accounting, locks, and encrypted response replays. Proofs and participant provider credentials are never stored. See `docs/hackathon-build/spec.md` for the full component, trust-boundary, data, failure, scale, cost, and deployment design.

## Public links

- Repository: https://github.com/KuantumKnight/gdg_llm_sandbox
- Live API: https://gdg-llm-sandbox-637q.onrender.com
- Interactive docs: https://gdg-llm-sandbox-637q.onrender.com/docs
- Demo video: **TODO — add the final public video URL**

## Testing instructions

```shell
uv sync --all-groups
uv run ruff format --check .
uv run ruff check .
uv run mypy app
uv run pytest --cov=app --cov-report=term-missing --cov-fail-under=85
uv run python scripts/scan_secrets.py
uv run python scripts/demo.py --mode stub
```

GitHub Actions also starts real Redis, executes the production Lua flow, builds the non-root image, waits for the Compose stack, and runs an in-container readiness probe. The local suite currently has 63 passing tests and one real-Redis test skipped without `TEST_REDIS_URL`; CI supplies that Redis variable and runs the skipped case.

## Screenshot shot list

1. Repository README hero with CI badge and live links.
2. Swagger UI showing the four versioned challenge endpoints.
3. Normal attempt response with `solved: false` and no hint.
4. Injection response with `solved: true`, session proof in model output, and the next-round hint.
5. GitHub Actions quality and container jobs passing.
6. Render service and private Key Value both healthy, with no secret values visible.

## Demo video outline (about 90 seconds)

1. **0:00-0:12 — Problem:** prompt injection should be the game, not an excuse for unsafe infrastructure.
2. **0:12-0:25 — Architecture:** point to stateless API, bounded provider gateway, session proof, and Redis atomic state.
3. **0:25-0:55 — Live flow:** use the custom participant interface to show a Gemini refusal, the verified transformation injection, solve verification, and hint.
4. **0:55-1:12 — Security/cost:** mention no raw prompt logging, no arbitrary provider URL, one provider call per idempotency key, quotas, output caps, and ambiguous charging.
5. **1:12-1:25 — Evidence:** show the passing CI jobs, 91% coverage, public repository, and live deployment.
6. **1:25-1:30 — Close:** restate the educational boundary and event-ready next step.

## Known limitations

- The public demo uses a real server-managed Gemini 3.5 Flash-Lite preset but still uses development admission and hint values; an actual event must enable production mode and rotate every organizer value.
- Free Render resources can cold-start and are not sized for an unbounded public launch.
- Model latency and prompt-injection behavior can change without an application release, so every provider revision requires recalibration.
- Session-specific proofs reduce answer sharing but do not stop participants from sharing injection techniques.
- The currently verified Gemini solution is documented for demonstration and must be replaced or withheld for a competitive round.

## Organizer checklist

- [ ] Start/register the actual Devpost hackathon workflow and acknowledge its current official rules.
- [ ] Load the official submission fields, judging criteria, deadlines, and media constraints.
- [ ] Replace demo round code, hint, crypto secrets, and observability token in Render.
- [x] Configure and calibrate a server-managed real provider preset.
- [x] Run a sacrificial normal/solve smoke flow with the selected real model.
- [ ] Capture the six screenshots without exposing credentials or participant content.
- [ ] Record and upload the demo video; add its public URL above.
- [ ] Reconcile this draft against official form wording and word limits.
- [ ] Run the final secret scan and confirm the CI run for the submission commit is green.

## Readiness

The product, architecture, repository, responsive participant interface, Gemini deployment, deterministic local demo, documentation, and automated evidence are ready for organizer hardening and media capture. Official event registration, rule review, production-secret rotation, form-specific copy, screenshots, and video remain deliberately unclaimed.
