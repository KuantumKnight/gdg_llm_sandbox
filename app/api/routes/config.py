from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import SettingsDep
from app.schemas.config import PublicConfigData, PublicConfigEnvelope, PublicPreset, PublicPrivacy

router = APIRouter(prefix="/api/v1", tags=["challenge"])


@router.get("/config", response_model=PublicConfigEnvelope)
async def public_config(settings: SettingsDep) -> PublicConfigEnvelope:
    return PublicConfigEnvelope(
        data=PublicConfigData(
            round_status="open",
            session_ttl_seconds=settings.session_ttl_seconds,
            attempt_limit=settings.attempt_limit,
            prompt_max_characters=settings.prompt_max_characters,
            idempotency_ttl_seconds=settings.idempotency_ttl_seconds,
            presets=[
                PublicPreset(
                    id=preset.id,
                    label=preset.label,
                    model_label=preset.model_label,
                    credential_mode=preset.credential_mode,
                )
                for preset in settings.public_presets()
            ],
            privacy=PublicPrivacy(
                provider_keys_retained=False,
                prompts_retained=False,
                encrypted_response_replay_ttl_seconds=settings.idempotency_ttl_seconds,
            ),
        )
    )
