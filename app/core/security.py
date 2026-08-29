"""Small, auditable security primitives used across the service."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SessionCredentials:
    session_id: str
    bearer_token: str


def new_session_credentials() -> SessionCredentials:
    """Return independent random public and secret session credentials."""
    return SessionCredentials(session_id=str(uuid.uuid4()), bearer_token=secrets.token_urlsafe(32))


def new_request_id() -> str:
    return str(uuid.uuid4())


def token_digest(token: str, pepper: str) -> str:
    """Create a non-reversible verification digest for a high-entropy bearer."""
    return hmac.new(pepper.encode(), token.encode(), hashlib.sha256).hexdigest()


def verify_token(token: str, expected_digest: str, pepper: str) -> bool:
    return hmac.compare_digest(token_digest(token, pepper), expected_digest)


def constant_time_secret_matches(candidate: str, expected: str) -> bool:
    """Compare admission and observability secrets without early-exit timing."""
    return hmac.compare_digest(candidate.encode(), expected.encode())


def opaque_identifier(value: str, secret: str, *, length: int = 16) -> str:
    """Create a stable, non-reversible identifier suitable for limits and logs."""
    digest = hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()
    return digest[:length]


def canonical_request_digest(*, method: str, path: str, body: dict[str, Any], secret: str) -> str:
    """HMAC a canonical request so an idempotency key cannot be reused for other input."""
    canonical = json.dumps(
        {"method": method.upper(), "path": path, "body": body},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hmac.new(secret.encode(), canonical, hashlib.sha256).hexdigest()


def idempotency_key_digest(value: str, secret: str) -> str:
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()
