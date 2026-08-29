from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import AppEnvironment, CredentialMode, ProviderPreset, Settings


def test_default_settings_are_development_safe() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_env is AppEnvironment.DEVELOPMENT
    assert settings.preset_by_id("stub-local") is not None
    assert settings.idempotency_ttl_seconds <= 600


def test_duplicate_preset_ids_are_rejected() -> None:
    preset = ProviderPreset(
        id="duplicate",
        label="Duplicate",
        model_label="Model",
        base_url="https://example.invalid/v1",
        model="model",
        credential_mode=CredentialMode.SERVER_MANAGED,
        server_api_key=SecretStr("key"),
    )

    with pytest.raises(ValidationError, match="unique"):
        Settings(provider_presets=[preset, preset], _env_file=None)


def test_production_rejects_placeholder_secrets() -> None:
    with pytest.raises(ValidationError, match="production secret"):
        Settings(app_env=AppEnvironment.PRODUCTION, _env_file=None)


def test_participant_preset_rejects_server_key() -> None:
    with pytest.raises(ValidationError, match="cannot define"):
        ProviderPreset(
            id="participant",
            label="Participant",
            model_label="Model",
            base_url="https://example.invalid/v1",
            model="model",
            credential_mode=CredentialMode.PARTICIPANT_PROVIDED,
            server_api_key=SecretStr("should-not-exist"),
        )


def test_wildcard_cors_is_rejected() -> None:
    with pytest.raises(ValidationError, match="wildcard"):
        Settings(cors_origins=["*"], _env_file=None)
