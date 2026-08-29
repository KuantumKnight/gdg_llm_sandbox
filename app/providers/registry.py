"""Provider factory constrained to operator-configured presets."""

from __future__ import annotations

from app.core.config import AppEnvironment, ProviderPreset, Settings
from app.providers.base import LLMProvider
from app.providers.errors import ProviderConfigurationError
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.providers.stub import DeterministicStubProvider


class ProviderRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get(self, preset_id: str) -> tuple[ProviderPreset, LLMProvider]:
        preset = self.settings.preset_by_id(preset_id)
        if preset is None:
            raise ProviderConfigurationError("provider preset is unavailable")
        if preset.id == "stub-local":
            if self.settings.app_env is AppEnvironment.PRODUCTION:
                raise ProviderConfigurationError("stub provider is disabled in production")
            return preset, DeterministicStubProvider()
        return preset, OpenAICompatibleProvider(
            preset, timeout_seconds=self.settings.provider_timeout_seconds
        )
