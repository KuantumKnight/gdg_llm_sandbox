# Operator Guide

## Production preflight

1. Create an isolated Render environment from `render.yaml`, or configure equivalent web and Key Value resources in the same region.
2. Set a high-entropy `ROUND_ACCESS_CODE` and distribute it out of band only when the round opens.
3. Set `NEXT_ROUND_HINT` to the organizer-approved next step.
4. Replace the development stub with at least one approved `PROVIDER_PRESETS` entry. Use HTTPS and a participant-provided or server-managed credential mode.
5. Confirm `APP_ENV=production`; startup must reject every development placeholder.
6. Run the quality gate, deployed smoke probe, and a sacrificial session before admitting participants.

Never paste a live connection string, provider key, bearer, proof, round code, or hint into GitHub issues, commits, logs, screenshots, or support messages.

## Runtime settings

| Setting | Recommended event value | Operational effect |
| --- | --- | --- |
| `SESSION_TTL_SECONDS` | `2700` | Participant session lifetime |
| `ATTEMPT_LIMIT` | `20` | Maximum chargeable calls per session |
| `SESSION_ATTEMPTS_PER_MINUTE` | `6` | Per-session token bucket capacity |
| `IP_SESSION_CREATIONS_PER_WINDOW` | `5` | Admission abuse control |
| `PROVIDER_TIMEOUT_SECONDS` | `30` | Total provider request bound |
| `MODEL_MAX_OUTPUT_TOKENS` | `512` | Per-call output cost cap |
| `PRESET_CONCURRENCY_LIMIT` | sized to provider quota | Shared in-flight provider cap |
| `IDEMPOTENCY_TTL_SECONDS` | `600` | Exact replay and unknown-outcome window |

Keep Redis on a private network with `noeviction`. Eviction can silently break locks, idempotency, and accounting; scaling memory or reducing admission is safer.

## Health and deployment

- `/health/live` proves only that the process can answer HTTP. Use it for container liveness.
- `/health/ready` verifies shared state. Use it for Render rollout health and traffic readiness.
- A deployment is complete only after readiness succeeds and `scripts/smoke.py` passes.
- Roll back application code through Render when a release fails. Do not change proof or digest secrets during an ordinary code rollback.

The repository's GitHub Actions workflow is required before auto-deploy: format, lint, strict types, 85% coverage, real Redis transitions, tracked-file secret scan, image build, Compose health, and container smoke.

## Secret rotation

Rotating some secrets invalidates live ephemeral state. Prefer a planned drain:

1. Stop new session admission by changing or withholding the round code.
2. Wait one maximum session TTL plus cleanup grace, or announce that sessions will reset.
3. Rotate the session pepper, proof secret, idempotency digest secret, replay key, observability token, and provider keys independently.
4. Redeploy, verify readiness, create a sacrificial session, and execute normal/replay/solve.
5. Reopen admission with the new round code.

An emergency provider-key or observability-token rotation should happen immediately. Existing participant sessions can remain valid when only those two credentials change.

## Monitoring and privacy

Scrape `/metrics` with `Authorization: Bearer <OBSERVABILITY_TOKEN>`. Alert on:

- readiness failures;
- increases in provider timeout/unavailable outcomes;
- preset concurrency saturation;
- unexpected session creation or attempt rates;
- sustained memory pressure on Key Value.

Logs intentionally contain only event, request ID, route template, method, status, preset ID, outcome, solve boolean, duration, token counts, and exception class. Do not add raw headers, bodies, query strings, IP addresses, prompts, responses, proofs, or hints to logs or metric labels.

## Incident response

### Redis unavailable

Readiness fails closed. Do not bypass Redis or fall back to process memory: that would break cross-replica authorization and accounting. Restore Key Value, confirm `PING`, then execute a sacrificial session.

### Provider degradation

Disable the affected preset or reduce its concurrency. Credential/rate failures are released; ambiguous dispatched failures remain charged and idempotently blocked. Never add automatic retries around the provider call.

### Suspected secret disclosure

Close admission, rotate the affected secret, invalidate sessions when the session/proof/replay secrets are involved, inspect only allowlisted telemetry, and document the incident without copying the leaked value.

### Unexpected solve sharing

Confirm proofs are session-specific and no prompt/response telemetry was enabled. Rotate the proof derivation secret only with a participant-session reset. Adjust the challenge prompt version between rounds rather than weakening infrastructure controls.

## Capacity and cost

The API is stateless and inexpensive; provider tokens dominate cost. Estimate the maximum round budget as admitted sessions × attempt limit × configured output cap, then reduce it using observed token averages. Raise web replicas only after checking Redis connection capacity and provider concurrency. No queue is used because attempts must return synchronously and idempotency already controls duplicate work.

## Event closeout

1. Stop admission and wait for in-flight requests to finish.
2. Export only aggregate metrics needed for the retrospective.
3. Rotate provider and observability credentials.
4. Allow ephemeral Redis keys to expire, then suspend or delete event resources according to organizer policy.
5. Do not retain prompts, model responses, proofs, bearer tokens, or participant provider keys.
