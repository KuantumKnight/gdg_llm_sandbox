from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.core.config import CredentialMode


class PublicPreset(BaseModel):
    id: str
    label: str
    model_label: str
    credential_mode: CredentialMode


class PublicPrivacy(BaseModel):
    provider_keys_retained: bool
    prompts_retained: bool
    encrypted_response_replay_ttl_seconds: int


class PublicConfigData(BaseModel):
    round_status: Literal["open", "unavailable"]
    session_ttl_seconds: int
    attempt_limit: int
    prompt_max_characters: int
    idempotency_ttl_seconds: int
    presets: list[PublicPreset]
    privacy: PublicPrivacy


class PublicConfigEnvelope(BaseModel):
    data: PublicConfigData
