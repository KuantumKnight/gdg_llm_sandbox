# Project Scope: GDG LLM Sandbox

## Source brief

Task 1 of the GDG Cloud & DevOps Round 2 brief asks for a backend system for a TechnoVIT prompt-injection round. The backend must accept a participant prompt, process it through an LLM, and return the result. The round solution must be embedded in the system prompt, whose resistance should be strong enough to make the challenge interesting but not impossible. The backend must be feasible, scalable, cost-efficient, reproducible in the cloud, and thoroughly documented.

The submission also requires a public GitHub repository, a deployment, a README that covers operation, data flow, security, access control, edge cases, problems, and mitigations, plus a working demonstration video of no more than five minutes.

## Product concept

The sandbox is an API-first prompt-injection game. A participant exchanges a round access code for a short-lived session, chooses an organizer-approved model/provider configuration, and submits prompts. For each session, the backend derives a unique proof token and embeds it in a defensive system prompt. The model is told not to reveal that token, while the participant attempts to override or extract it. If the model response contains the session's exact proof token, the backend marks the session solved and returns the next-round hint.

The LLM boundary is intentionally vulnerable. The surrounding web service is not: credentials, provider URLs, quotas, session authorization, logs, and deployment configuration remain protected.

## Primary users

- Participant: attempts the challenge through the API or interactive API documentation.
- Organizer/operator: configures the round, model allowlist, budget limits, access codes, and next-round hint; monitors health and aggregate usage.
- Developer/reviewer: runs the system locally, tests it, studies the architecture, and deploys the same container to the cloud.

## In scope for the working core

- Round access-code exchange and short-lived participant sessions.
- Session-specific proof token derived from a server secret and embedded only in the LLM system prompt.
- Prompt submission to an organizer-approved LLM provider/model.
- Server-managed credentials and participant-provided credentials.
- OpenAI-compatible provider abstraction for third-party and self-hosted models.
- Automatic solve detection from model output and one-time hint reveal.
- Redis-backed session state, idempotency, distributed quotas, and rate limits.
- Request validation, timeouts, bounded retries, redacted structured logs, health checks, and metrics.
- Docker-based local reproduction and a Render deployment path.
- Automated unit, integration, contract, and security tests.
- API documentation and a demonstration-ready flow.

## Explicit non-goals for the first release

- A full participant website or mobile app; FastAPI's interactive documentation is enough for the backend round and demo.
- User accounts, password recovery, social login, or long-lived profiles; the event already controls participant admission.
- A public leaderboard, team management, or judging workflow; these are event-platform concerns rather than the prompt-injection core.
- Arbitrary participant-supplied provider base URLs; allowing them would create an SSRF and data-exfiltration surface.
- Storing raw prompts, responses, or participant provider keys for analytics or durable history; a completed response may exist briefly in an encrypted idempotency replay record.
- A general-purpose LLM proxy or multi-turn chat product.
- Perfect prompt-injection prevention; that would defeat the challenge.
- Kubernetes, a message queue, or a relational database for the initial event workload.

## Success measures

- A new reviewer can start the API and Redis locally with one documented command.
- An authorized participant can create a session and receive a model response in two API calls.
- A successful injection is recognized only when the model output contains the correct session-specific proof token.
- The next-round hint is never sent before a successful solve.
- Participant provider keys and challenge secrets never appear in application state or logs.
- Duplicate retries do not cause duplicate provider charges when an idempotency key is reused.
- Multiple API instances share sessions and rate limits through Redis.
- Provider failures degrade into stable, documented API errors without crashing the service.

## Time and delivery assumptions

- The project is optimized for a short hackathon build and demonstration.
- The first deployment targets one API service plus one managed Redis-compatible store.
- One OpenAI-compatible model path is sufficient for the core; additional provider presets are adapters, not separate application flows.
- Organizers supply the actual round access code, secret material, model allowlist, and next-round hint through environment variables or secret management.
