# Product Requirements Document: GDG LLM Sandbox

## Product Summary

GDG LLM Sandbox is an API-first challenge for a TechnoVIT event round. An authorized participant sends instructions to an LLM that has been given a secret proof token in its system prompt. The system prompt tells the model to protect the token, but it is intentionally only moderately resistant: extracting the token through prompt injection is the challenge, not a security incident.

Every session receives a different proof token. The participant wins only when the LLM itself emits that session's token. The backend then verifies the response and reveals the next-round hint. This preserves the intended prompt-injection experience while reducing answer sharing and keeping event infrastructure, credentials, configuration, and the hint protected.

The first release is a focused backend experience exposed through a documented HTTP API and interactive API console. It is designed to be cheap to operate for hundreds of participants, quick to reproduce locally or in the cloud, and easy for reviewers to understand.

## Product Principles

- **Break the prompt, not the platform.** Prompt injection is allowed and encouraged; attempts to bypass access controls, quotas, provider restrictions, or infrastructure boundaries are not.
- **Interesting, not impossible.** The system prompt provides meaningful resistance without an output filter that makes disclosure impossible.
- **No surprise spending.** Participants always see attempt limits and stable errors; organizers can enforce a finite event budget.
- **Credentials are transient.** A participant-provided provider key is used only for the current request and is never retained by the sandbox.
- **One short path to the wow moment.** A reviewer can create a session, try an ordinary prompt, perform an injection, and unlock the hint in a few minutes.
- **Failure is understandable.** Empty inputs, expired sessions, provider outages, rate limits, and invalid credentials produce distinct guidance rather than generic failures.

## Target Users

### Participant

A technically curious event participant who can use an HTTP API or interactive API console. They want a fair prompt-injection puzzle, immediate feedback, and a clear signal when they have solved it.

### Organizer/operator

An event organizer who needs to admit only round participants, control cost and model choices, change the hidden hint without a code change, and confirm that the service is healthy without seeing participant credentials or raw attempts.

### Reviewer/developer

A judge or developer who wants to understand the decisions, run the same flow locally, verify edge cases, and reproduce the deployed behavior.

## Assumptions

- The event distributes a round access code to eligible participants through an existing channel.
- Participants use one of the model/provider choices enabled by the organizer.
- A model may use either an organizer-funded credential or a participant-supplied credential, depending on the configured provider.
- Sessions are short-lived and do not need to survive beyond the event window.
- The next-round hint is the protected reward; aggregate operational metrics are useful, but raw participant conversations are not required.
- A session-specific proof token satisfies the brief's requirement that the solution be embedded in the system prompt.

## Core User Journey

1. The participant opens the API guide and sees the challenge rules, supported provider choices, credential mode, prompt/attempt limits, and privacy statement.
2. The participant submits the round access code and selects an allowed provider/model.
3. The sandbox returns a session identifier, a session authorization token, an expiry time, and the remaining-attempt allowance. It never returns the hidden proof token.
4. The participant submits an ordinary prompt. The LLM responds normally or refuses to discuss the protected token. The response says the session is not yet solved and shows remaining attempts.
5. The participant iterates on prompt-injection techniques. Each accepted attempt produces exactly one model response and one clear challenge result.
6. When the LLM response contains the exact proof token for that session, the same response is marked solved and includes the next-round hint.
7. Later requests to the solved session report that it is already solved and repeat the same hint without spending another model call.

## Epics And User Stories

### Epic 1: Understand and enter the round

#### PRD-1.1 - Read the challenge contract

As a participant, I want to see the challenge rules and request examples before spending an attempt so that I know what is allowed and how to begin.

Acceptance criteria:

- The API guide identifies prompt injection as the intended challenge and clearly separates allowed prompt attacks from prohibited infrastructure abuse.
- The guide shows the supported providers/models, the credential requirement for each choice, the maximum prompt size, the attempt allowance, the session lifetime, and a privacy statement.
- The guide includes a complete example for session creation and prompt submission with placeholder credentials only.
- No real access code, provider key, system prompt, proof token, server secret, or next-round hint appears in the guide.

#### PRD-1.2 - Exchange round access for a session

As an eligible participant, I want to create a temporary challenge session so that my attempts and result are isolated from other participants.

Acceptance criteria:

- A valid round access code and allowed provider/model selection return a new session.
- The session result includes a session identifier, authorization token, creation time, expiry time, provider/model label, and attempt allowance.
- The session result does not expose the proof token, system prompt, next-round hint, or any server credential.
- A wrong or missing round access code returns an access-denied response and does not create a session.
- A provider/model outside the visible allowlist returns a selection error that lists only permitted public choices.
- Repeating session creation creates a distinct session and distinct authorization token.

### Epic 2: Choose who pays for the model call

#### PRD-2.1 - Use an organizer-funded provider

As a participant, I want to use an organizer-funded provider when one is enabled so that I can play without owning an API key.

Acceptance criteria:

- An organizer-funded choice is visibly labeled as not requiring a participant key.
- Sending a participant provider key for that choice is unnecessary and does not change the configured model.
- If the organizer-funded allowance is exhausted, the participant sees a budget-unavailable response before a new model call begins.
- The response never reveals the organizer's provider account, key, balance, or internal quota values.

#### PRD-2.2 - Use my own provider credential

As a participant, I want to supply my own provider key for a supported choice so that I can play even when the organizer does not fund that model.

Acceptance criteria:

- A participant-funded choice is visibly labeled as requiring a key on each attempt.
- A missing key produces a credential-required response without consuming an attempt.
- An invalid or rejected provider key produces a provider-authentication response without echoing the submitted key.
- The privacy statement says that the key is forwarded only for the current model request and is not retained by the sandbox.
- Returning to a later attempt requires the key again, demonstrating that the sandbox did not save it.

### Epic 3: Attempt the prompt-injection challenge

#### PRD-3.1 - Submit a bounded prompt

As a participant, I want to submit one prompt and receive one LLM response so that I can test an injection strategy and learn from the outcome.

Acceptance criteria:

- An authorized, active session accepts a non-empty text prompt within the published size limit.
- The result includes an attempt identifier, the model's text response, solved status, remaining attempts, and a request correlation identifier.
- An unsolved response never includes the next-round hint as a separate field.
- Whitespace-only, oversized, structurally invalid, or unsupported content is rejected before a model call and does not consume an attempt.
- The sandbox accepts prompt-injection language, encoded instructions, role-play, and requests to ignore prior instructions; these are not blocked merely because they are attacks on the system prompt.
- The first release accepts text only; files, images, audio, tool calls, and external URLs are rejected as unsupported input.

#### PRD-3.2 - Receive stable feedback under load

As a participant, I want a clear result even when the event is busy so that I know whether to retry, wait, or change my prompt.

Acceptance criteria:

- A request accepted for processing returns either a model result or a documented error; it does not hang indefinitely.
- Rate-limited requests show when a retry is allowed and do not consume an attempt.
- A session with another attempt already in progress receives a busy response instead of starting an extra model call.
- A provider timeout or temporary provider outage produces a retryable error and does not falsely mark the session solved.
- A duplicate retry carrying the same idempotency value returns the original completed result and does not consume another attempt or create another charge.
- A duplicate retry still in progress reports that state instead of initiating another call.

#### PRD-3.3 - See fair attempt accounting

As a participant, I want attempts to be counted consistently so that transient failures do not unfairly end my round.

Acceptance criteria:

- Validation failures, access failures, rate limits, duplicate replays, and sandbox infrastructure failures do not reduce the remaining-attempt count.
- An attempt is charged once the provider accepts the model request, even if the model refuses to reveal the token.
- The response after every valid attempt shows the remaining count.
- When no attempts remain, the sandbox rejects new model calls and reports that the allowance is exhausted.
- Attempt counts remain consistent when requests reach different running copies of the API.

### Epic 4: Verify a solve and reveal the reward

#### PRD-4.1 - Detect the session's proof token

As a participant, I want the sandbox to recognize the proof token when the model reveals it so that success is immediate and objective.

Acceptance criteria:

- The session is solved only when the model output contains the exact proof token derived for that session.
- The participant's input alone cannot mark the session solved; verification uses the model response.
- A token from another session does not solve the current session.
- Similar-looking text, a partial token, different casing, added characters inside the token, or a decoy token does not count.
- The successful attempt result is marked solved in the same response; the participant does not need a separate verification request.

#### PRD-4.2 - Unlock the next-round hint once

As a successful participant, I want the next-round hint returned immediately so that I can continue the event.

Acceptance criteria:

- The first successful response includes the configured next-round hint and a solved timestamp.
- The hint is absent from all session and attempt responses before success.
- Reading an already solved session returns solved status and the same hint without making an LLM call or reducing attempts.
- Additional attempt submissions to a solved session do not make an LLM call and direct the participant to the solved-session result.
- The system does not expose another session's result or hint when presented with the wrong session authorization token.

### Epic 5: Preserve access, privacy, and challenge boundaries

#### PRD-5.1 - Keep sessions isolated

As a participant, I want only my session authorization to access my state so that other participants cannot inspect or spend my attempts.

Acceptance criteria:

- Session details and attempts require the authorization token issued for that exact session.
- Missing, malformed, expired, or mismatched authorization receives the same generic unauthorized result and does not disclose whether a session identifier exists.
- An expired session cannot start new model calls.
- Session authorization is not accepted as a round access code and the round access code is not accepted as session authorization.

#### PRD-5.2 - Minimize retained sensitive data

As a participant, I want my provider key and prompt content handled minimally so that playing the challenge does not create unnecessary credential or privacy risk.

Acceptance criteria:

- The sandbox never returns a submitted provider key in success or error responses.
- The published privacy behavior states that participant keys, raw prompts, raw model responses, system prompts, and proof tokens are not retained in shared session storage or application logs by default.
- Operational records use identifiers, counts, durations, result categories, and token-usage totals rather than raw content.
- When the session expires, its authorization state, attempt metadata, idempotency records, and solved state become unavailable after the documented cleanup window.

#### PRD-5.3 - Keep the puzzle intentionally solvable

As a participant, I want a genuine chance to bypass the model instruction so that the task tests prompt injection rather than guessing an impossible secret.

Acceptance criteria:

- The proof token is present in the system prompt sent to the selected model for every charged attempt.
- The system prompt instructs the model to protect the token and resist common override requests.
- The sandbox does not remove or replace a correctly revealed proof token from model output before verification.
- The sandbox does not reject an attempt solely because it contains known prompt-injection patterns.
- Organizers can adjust the wording and model choice to tune difficulty without changing the participant workflow.

### Epic 6: Operate and demonstrate the round

#### PRD-6.1 - Configure the event safely

As an organizer, I want to configure the access code, enabled providers/models, credential modes, budgets, challenge wording, session limits, and hint outside the source code so that deployment-specific secrets are not committed.

Acceptance criteria:

- Startup fails with a clear configuration error if required secret values are missing or placeholder values are used in a production environment.
- Public provider labels are separate from private provider endpoints and credentials.
- The organizer can disable a provider/model without affecting existing source files.
- Changing the next-round hint or round access code does not require editing application code.

#### PRD-6.2 - Observe service health without observing secrets

As an organizer, I want health and aggregate usage signals so that I can respond to failures and budget pressure during the event.

Acceptance criteria:

- A public liveness check reports only whether the process is running.
- A readiness check reports whether required shared services are available without exposing connection strings or credentials.
- Protected aggregate metrics show request counts, response categories, latency, active sessions, solved count, provider error count, and model-token totals.
- Health, metrics, and logs do not include round access codes, session authorization tokens, provider keys, system prompts, proof tokens, next-round hints, or raw participant/model content.

#### PRD-6.3 - Reproduce the judge demo

As a reviewer, I want a documented short demonstration so that I can verify the working core and major design claims within five minutes.

Acceptance criteria:

- The documented demo begins from a clean local or deployed environment and identifies the active provider mode.
- It demonstrates denied access, successful session creation, a normal unsolved attempt, a successful injection, and the unlocked hint.
- It demonstrates one cost-protection behavior such as idempotent replay, rate limiting, or exhausted attempts.
- It shows that logs omit the submitted provider key and challenge content.
- The same public repository contains setup instructions, architecture/data-flow documentation, security and edge-case notes, and automated test commands.

## Edge Cases

### Before the first action

- If no provider is enabled, the public configuration shows the round as temporarily unavailable and session creation is disabled.
- If the shared session store is unavailable, readiness fails and the API does not create local-only sessions that would disappear on another instance.
- If a participant does not own a provider key, the documentation makes clear which organizer-funded choice, if any, is usable.

### Session creation

- Repeated wrong access codes receive generic denial and are rate-limited without revealing the valid code format.
- Unknown provider and model values do not reveal private endpoint names or internal configuration.
- A session created just before an access-code rotation remains valid until its own expiry unless the organizer explicitly revokes all sessions.
- Concurrent session-creation requests each receive independent session authorization.

### Attempt submission

- Empty or whitespace-only text, extremely long Unicode input, invalid encodings, malformed JSON, unsupported media, and extra unknown fields are rejected consistently.
- Participant text that resembles system or developer message markup remains user text; the API does not allow the participant to choose a higher message role.
- A participant cannot choose the provider base URL, output limit, temperature, system prompt, or hidden token.
- Disconnecting after a provider call starts may still consume one attempt; replaying the same idempotency value retrieves the result when available.
- If the provider returns no text, malformed output, a safety refusal, or a truncated answer, the attempt remains unsolved and returns a documented outcome.
- If the model produces the proof token across formatting boundaries, only the documented exact contiguous token format counts.

### Solve and expiry

- Two concurrent responses that both contain the proof token produce one solved transition and the same solved result.
- A session that expires while a model call is in flight may complete that charged attempt, but no later attempt can begin.
- An expired unsolved session cannot be revived; the participant creates a new session with a new proof token.
- Rotating the server derivation secret invalidates unsolved tokens from older sessions; this is an explicit organizer emergency action.

### Provider and infrastructure failure

- Provider authentication failure is distinct from sandbox session authorization failure.
- Provider quota exhaustion, rate limiting, timeout, invalid model, and malformed response map to stable participant-facing categories.
- Automatic retries are limited to failures known to be safe to retry and never create unbounded charges.
- If shared state cannot be updated after a provider response, the request returns a recoverable error and an idempotent retry reconciles the result rather than silently starting over.

## What We Are Building

- A versioned HTTP API with interactive documentation.
- Temporary authorized sessions and organizer-configured provider choices.
- Unique hidden proof tokens embedded in a moderately defensive system prompt.
- Single-turn text attempts, LLM responses, exact solve detection, and hint unlock.
- Participant-funded and organizer-funded credential modes.
- Distributed attempt accounting, rate limiting, concurrency control, and idempotent replay.
- Privacy-preserving logs, health checks, protected metrics, automated tests, Docker setup, and cloud deployment configuration.
- A README and concise demo path aligned to the evaluation rubric.

## What We Would Add With More Time

- An organizer dashboard with live aggregate event status and emergency provider controls.
- A participant web interface that wraps the same API without changing challenge behavior.
- Multiple difficulty profiles and A/B-tested system prompts.
- Signed team invitations, team-based quotas, and a leaderboard.
- A durable audit stream with opt-in content capture and explicit retention controls.
- Additional first-class provider adapters when their behavior differs from OpenAI compatibility.
- Region-aware provider routing and automated budget failover.
- Abuse detection around infrastructure attacks while continuing to allow prompt attacks.
- A challenge-authoring tool for future rounds and reusable scoring plugins.

## Submission Proof Points

- **Documentation:** PRD, architecture diagrams, API contract, data lifecycle, threat boundaries, decision notes, edge cases, and a README that explains problems and mitigations.
- **Code quality:** explicit application layers, provider interfaces, typed request/response models, centralized error mapping, dependency injection, and focused automated tests.
- **Scalability and cost efficiency:** stateless API replicas, shared ephemeral state, distributed rate limits, bounded concurrency, model/token caps, idempotency, and no unnecessary relational database or queue.
- **Reproducibility and development:** locked dependencies, Docker image, local composition, example environment file, deterministic test doubles, CI, health checks, and infrastructure-as-code deployment.
- **Tech stack:** asynchronous Python API, Redis-compatible shared state, OpenAI-compatible provider protocol, container deployment, and standard observability interfaces.
- **Five-minute wow moment:** an ordinary refusal followed by a successful injection, automatic session-specific verification, and immediate next-round hint reveal.

## Product Acceptance Gate

The MVP is ready to demonstrate when every acceptance criterion in PRD-1 through PRD-6 that applies to the enabled provider mode has an automated or documented manual verification, the complete core journey succeeds against at least one real model, and no critical secret appears in repository history, API responses, shared state inspection, or logs.

