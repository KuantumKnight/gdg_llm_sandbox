from __future__ import annotations

from app.core.security import (
    canonical_request_digest,
    constant_time_secret_matches,
    new_session_credentials,
    opaque_identifier,
    token_digest,
    verify_token,
)


def test_session_credentials_are_independent_and_high_entropy() -> None:
    first = new_session_credentials()
    second = new_session_credentials()

    assert first.session_id != second.session_id
    assert first.bearer_token != second.bearer_token
    assert len(first.bearer_token) >= 43


def test_bearer_digest_verification() -> None:
    digest = token_digest("participant-token", "pepper")

    assert verify_token("participant-token", digest, "pepper")
    assert not verify_token("wrong", digest, "pepper")
    assert "participant-token" not in digest


def test_canonical_request_digest_binds_body_and_path() -> None:
    first = canonical_request_digest(
        method="post", path="/sessions/one/attempts", body={"prompt": "hello"}, secret="s"
    )
    same = canonical_request_digest(
        method="POST", path="/sessions/one/attempts", body={"prompt": "hello"}, secret="s"
    )
    different = canonical_request_digest(
        method="POST", path="/sessions/two/attempts", body={"prompt": "hello"}, secret="s"
    )

    assert first == same
    assert first != different


def test_opaque_identifiers_do_not_expose_input() -> None:
    identifier = opaque_identifier("192.0.2.1", "server-secret")

    assert identifier == opaque_identifier("192.0.2.1", "server-secret")
    assert "192.0.2.1" not in identifier
    assert len(identifier) == 16


def test_constant_time_secret_helper_has_expected_result() -> None:
    assert constant_time_secret_matches("expected", "expected")
    assert not constant_time_secret_matches("wrong", "expected")
