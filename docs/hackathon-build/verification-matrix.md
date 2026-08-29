# Verification Matrix

This matrix connects every product epic and critical architecture boundary to executable evidence. The default suite is deterministic and makes no paid or external model calls.

| Product surface | Primary automated evidence | Key behavior proved |
| --- | --- | --- |
| Epic 1 - entry | `tests/api/test_config.py`, `tests/api/test_sessions.py` | Safe public configuration, generic admission denial, one-time bearer return, expiry, and cross-session isolation |
| Epic 2 - credential modes | `tests/contract/test_openai_compatible.py`, `tests/unit/test_provider_registry.py` | Fixed provider destination/model/roles, request-scoped participant keys, server-managed keys, no SDK retry |
| Epic 3 - attempts | `tests/api/test_attempts.py`, `tests/integration/test_attempt_concurrency.py`, `tests/integration/test_attempt_failure_semantics.py` | Validation, one-provider-call reservation, exact replay, charging release, and ambiguous-timeout accounting |
| Epic 4 - solve and reward | `tests/unit/test_challenge.py`, `tests/api/test_attempts.py`, `tests/integration/test_redis_repositories.py` | Per-session proof derivation, output-only verification, atomic first solve, no hint before solve |
| Epic 5 - boundaries and privacy | `tests/security/`, `tests/unit/test_security.py`, `tests/unit/test_replay_crypto.py` | Authorization, HMAC request binding, encrypted replay, safe headers, closed CORS, secret/log/OpenAPI redaction |
| Epic 6 - operations and demo | `tests/api/test_health.py`, `tests/api/test_metrics.py`, production configuration tests | Liveness/readiness split, protected bounded metrics, fail-fast production settings |
| Shared state | `tests/integration/test_redis_repositories.py`, `tests/integration/test_real_redis.py` | The same Lua scripts preserve quotas, locks, idempotency, replay, TTL, and solve state on fake and real Redis |
| Model boundary | deterministic `stub-local` plus mocked OpenAI-compatible clients | No paid calls in CI; malformed and failing providers are controlled without arbitrary endpoints |

## Required quality gate

```shell
uv run ruff format --check .
uv run ruff check .
uv run mypy app
uv run pytest --cov=app --cov-report=term-missing --cov-fail-under=85
```

The real-Redis test activates when `TEST_REDIS_URL` points to an isolated database. Its fixture creates a unique namespace and removes only keys under that namespace. Without that variable it is explicitly skipped; the in-memory Redis suite still executes the identical checked-in Lua scripts.

## Manual deployment gates

- Verify `/health/live` succeeds without Redis and `/health/ready` fails closed when Redis is unavailable.
- Verify a deployed session can complete the normal, solve, and idempotent replay flow.
- Inspect the resulting Redis namespace and application logs for the sentinel prompt, proof, hint, bearer, round code, and provider key; none may appear in plaintext.
- Confirm that a second replica shares session, attempt, and solved state when horizontal scaling is enabled.
