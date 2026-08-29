"""Prompt-injection challenge construction and exact solve verification."""

from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime
from pathlib import Path

from app.domain.entities import ChallengeMessages

PROMPT_VERSION = "gatekeeper-v1"
PROOF_PREFIX = "GDG{"
PROOF_SUFFIX = "}"
_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / f"{PROMPT_VERSION}.txt"


class PromptTemplateError(RuntimeError):
    """Raised when a shipped challenge template is malformed."""


def derive_proof_token(*, session_id: str, created_at: datetime, secret: str) -> str:
    """Derive an ASCII session proof without storing it in shared state."""
    material = f"v1:{session_id}:{int(created_at.timestamp())}".encode()
    digest = hmac.new(secret.encode(), material, hashlib.sha256).digest()
    encoded = base64.b32encode(digest[:13]).decode("ascii").rstrip("=")[:20]
    return f"{PROOF_PREFIX}{encoded}{PROOF_SUFFIX}"


def render_challenge_messages(*, proof_token: str, user_prompt: str) -> ChallengeMessages:
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    placeholder = "{{ proof_token }}"
    if template.count(placeholder) != 1:
        raise PromptTemplateError("challenge template must contain exactly one proof placeholder")
    return ChallengeMessages(system=template.replace(placeholder, proof_token), user=user_prompt)


def model_output_solves(*, expected_proof: str, model_output: str) -> bool:
    """Only exact, case-sensitive, contiguous model output counts as a solve."""
    return expected_proof in model_output
