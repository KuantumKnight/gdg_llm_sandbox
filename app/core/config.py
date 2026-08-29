"""Validated runtime configuration."""

from __future__ import annotations

import ipaddress
from enum import StrEnum
from functools import lru_cache
from typing import Self
from urllib.parse import urlparse

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class CredentialMode(StrEnum):
    SERVER_MANAGED = "server_managed"
    PARTICIPANT_PROVIDED = "participant_provided"


class ProviderPreset(BaseModel):
    """Operator-controlled model configuration exposed through a public identifier."""

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,62}$")
    label: str = Field(min_length=1, max_length=80)
    model_label: str = Field(min_length=1, max_length=100)
    base_url: str
    model: str = Field(min_length=1, max_length=120)
    credential_mode: CredentialMode
    server_api_key: SecretStr | None = None
    enabled: bool = True

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("provider base_url must be an absolute HTTP(S) URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("provider base_url cannot contain credentials, query, or fragment")
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_credential_mode(self) -> Self:
        if self.credential_mode is CredentialMode.SERVER_MANAGED and not self.server_api_key:
            raise ValueError("server-managed presets require server_api_key")
        if self.credential_mode is CredentialMode.PARTICIPANT_PROVIDED and self.server_api_key:
            raise ValueError("participant-provided presets cannot define server_api_key")
        return self


def _development_preset() -> ProviderPreset:
    return ProviderPreset(
        id="stub-local",
        label="Deterministic local stub",
        model_label="Stub model",
        base_url="https://stub.invalid/v1",
        model="stub-model",
        credential_mode=CredentialMode.SERVER_MANAGED,
        server_api_key=SecretStr("dev-provider-key"),
    )


class Settings(BaseSettings):
    """Application settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    app_name: str = "GDG LLM Sandbox"
    log_level: str = "INFO"
    redis_url: SecretStr = SecretStr("redis://localhost:6379/0")

    round_access_code: SecretStr = SecretStr("dev-round-access-code")
    session_token_pepper: SecretStr = SecretStr("dev-session-token-pepper-change-me")
    proof_derivation_secret: SecretStr = SecretStr("dev-proof-derivation-secret-change-me")
    idempotency_digest_secret: SecretStr = SecretStr("dev-idempotency-digest-secret-change-me")
    replay_encryption_key: SecretStr = SecretStr("ZGV2LXJlcGxheS1lbmNyeXB0aW9uLWtleS0wMDAwMDA=")
    next_round_hint: SecretStr = SecretStr("Development hint: configure the real next-round clue.")
    observability_token: SecretStr = SecretStr("dev-observability-token-change-me")

    provider_presets: list[ProviderPreset] = Field(default_factory=lambda: [_development_preset()])

    session_ttl_seconds: int = Field(default=2700, ge=300, le=14400)
    session_cleanup_grace_seconds: int = Field(default=300, ge=30, le=1800)
    attempt_limit: int = Field(default=20, ge=1, le=100)
    prompt_max_characters: int = Field(default=4000, ge=100, le=20000)
    model_max_output_tokens: int = Field(default=512, ge=32, le=2048)
    session_attempts_per_minute: int = Field(default=6, ge=1, le=60)
    ip_session_creations_per_window: int = Field(default=5, ge=1, le=100)
    ip_session_window_seconds: int = Field(default=600, ge=60, le=3600)
    provider_timeout_seconds: float = Field(default=30.0, ge=3, le=120)
    idempotency_ttl_seconds: int = Field(default=600, ge=60, le=600)
    request_body_limit_bytes: int = Field(default=16384, ge=1024, le=131072)
    preset_concurrency_limit: int = Field(default=25, ge=1, le=1000)
    cors_origins: list[str] = Field(default_factory=list)

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("unsupported log level")
        return normalized

    @field_validator("provider_presets")
    @classmethod
    def require_unique_presets(cls, value: list[ProviderPreset]) -> list[ProviderPreset]:
        ids = [preset.id for preset in value]
        if len(ids) != len(set(ids)):
            raise ValueError("provider preset ids must be unique")
        if not any(preset.enabled for preset in value):
            raise ValueError("at least one provider preset must be enabled")
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError("wildcard CORS origins are not permitted")
        return [origin.rstrip("/") for origin in value]

    @model_validator(mode="after")
    def validate_production_safety(self) -> Self:
        if self.app_env is not AppEnvironment.PRODUCTION:
            return self

        secret_fields = (
            "round_access_code",
            "session_token_pepper",
            "proof_derivation_secret",
            "idempotency_digest_secret",
            "replay_encryption_key",
            "next_round_hint",
            "observability_token",
        )
        for field_name in secret_fields:
            secret = getattr(self, field_name).get_secret_value()
            if len(secret) < 24 or secret.lower().startswith(("dev-", "change", "example")):
                raise ValueError(f"{field_name} must be a non-placeholder production secret")

        for preset in self.provider_presets:
            parsed = urlparse(preset.base_url)
            host = parsed.hostname or ""
            is_loopback = False
            try:
                is_loopback = ipaddress.ip_address(host).is_loopback
            except ValueError:
                is_loopback = host == "localhost"
            if parsed.scheme != "https" and not is_loopback:
                raise ValueError(f"production preset {preset.id} must use HTTPS")
            if preset.server_api_key:
                key = preset.server_api_key.get_secret_value()
                if key.lower().startswith(("dev-", "change", "example")):
                    raise ValueError(f"production preset {preset.id} uses a placeholder key")
        return self

    def public_presets(self) -> list[ProviderPreset]:
        return [preset for preset in self.provider_presets if preset.enabled]

    def preset_by_id(self, preset_id: str) -> ProviderPreset | None:
        return next((preset for preset in self.public_presets() if preset.id == preset_id), None)


@lru_cache
def get_settings() -> Settings:
    return Settings()
