"""Authenticated encryption for short-lived idempotency replay responses."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class ReplayCryptoError(ValueError):
    """Replay encryption configuration or authentication failure."""


@dataclass(frozen=True, slots=True)
class ReplayCiphertext:
    version: str
    nonce: str
    ciphertext: str

    def serialize(self) -> str:
        return json.dumps(
            {"v": self.version, "n": self.nonce, "c": self.ciphertext},
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def parse(cls, value: str) -> ReplayCiphertext:
        try:
            raw = json.loads(value)
            return cls(version=raw["v"], nonce=raw["n"], ciphertext=raw["c"])
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ReplayCryptoError("invalid replay envelope") from exc


class ReplayCrypto:
    """Versioned AES-256-GCM encryption with caller-provided associated data."""

    def __init__(self, encoded_key: str, *, key_version: str = "v1") -> None:
        try:
            key = base64.urlsafe_b64decode(encoded_key.encode())
        except (ValueError, TypeError) as exc:
            raise ReplayCryptoError("replay key must be valid URL-safe base64") from exc
        if len(key) != 32:
            raise ReplayCryptoError("replay key must decode to exactly 32 bytes")
        self._aes = AESGCM(key)
        self.key_version = key_version

    def encrypt(self, payload: dict[str, Any], *, associated_data: str) -> str:
        nonce = os.urandom(12)
        plaintext = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        ciphertext = self._aes.encrypt(nonce, plaintext, self._aad(associated_data))
        return ReplayCiphertext(
            version=self.key_version,
            nonce=base64.urlsafe_b64encode(nonce).decode(),
            ciphertext=base64.urlsafe_b64encode(ciphertext).decode(),
        ).serialize()

    def decrypt(self, envelope: str, *, associated_data: str) -> dict[str, Any]:
        parsed = ReplayCiphertext.parse(envelope)
        if parsed.version != self.key_version:
            raise ReplayCryptoError("unknown replay key version")
        try:
            nonce = base64.urlsafe_b64decode(parsed.nonce.encode())
            ciphertext = base64.urlsafe_b64decode(parsed.ciphertext.encode())
            plaintext = self._aes.decrypt(nonce, ciphertext, self._aad(associated_data))
            decoded = json.loads(plaintext)
        except (ValueError, InvalidTag, json.JSONDecodeError) as exc:
            raise ReplayCryptoError("replay authentication failed") from exc
        if not isinstance(decoded, dict):
            raise ReplayCryptoError("replay payload must be an object")
        return decoded

    def _aad(self, associated_data: str) -> bytes:
        return f"gdg-llm-sandbox:{self.key_version}:{associated_data}".encode()
