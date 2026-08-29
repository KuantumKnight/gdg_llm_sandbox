from __future__ import annotations

import base64
import json

import pytest

from app.services.replay_crypto import ReplayCrypto, ReplayCryptoError


def encoded_key(fill: bytes = b"k") -> str:
    return base64.urlsafe_b64encode(fill * 32).decode()


def test_replay_round_trip_and_plaintext_absence() -> None:
    crypto = ReplayCrypto(encoded_key())
    payload = {"status": 200, "model_response": "sensitive output"}

    envelope = crypto.encrypt(payload, associated_data="session:idem")

    assert "sensitive output" not in envelope
    assert crypto.decrypt(envelope, associated_data="session:idem") == payload


def test_tampering_fails_closed() -> None:
    crypto = ReplayCrypto(encoded_key())
    raw = json.loads(crypto.encrypt({"ok": True}, associated_data="a"))
    raw["c"] = raw["c"][:-2] + "AA"

    with pytest.raises(ReplayCryptoError, match="authentication"):
        crypto.decrypt(json.dumps(raw), associated_data="a")


def test_associated_data_binds_replay_to_lookup_key() -> None:
    crypto = ReplayCrypto(encoded_key())
    envelope = crypto.encrypt({"ok": True}, associated_data="session-one:key")

    with pytest.raises(ReplayCryptoError, match="authentication"):
        crypto.decrypt(envelope, associated_data="session-two:key")


def test_invalid_key_length_is_rejected() -> None:
    with pytest.raises(ReplayCryptoError, match="32 bytes"):
        ReplayCrypto(base64.urlsafe_b64encode(b"short").decode())
