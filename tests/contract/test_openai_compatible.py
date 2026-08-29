from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import SecretStr

from app.core.config import CredentialMode, ProviderPreset
from app.providers.base import ProviderRequest
from app.providers.errors import ProviderCredentialRequiredError
from app.providers.openai_compatible import OpenAICompatibleProvider


class FakeCompletions:
    def __init__(self, capture: dict[str, Any]) -> None:
        self.capture = capture

    async def create(self, **kwargs: Any) -> Any:
        self.capture["request"] = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="model output"))],
            usage=SimpleNamespace(prompt_tokens=12, completion_tokens=3),
            _request_id="provider-request-id",
        )


class FakeClient:
    def __init__(self, capture: dict[str, Any], **kwargs: Any) -> None:
        capture["client"] = kwargs
        self.capture = capture
        self.chat = SimpleNamespace(completions=FakeCompletions(capture))

    async def close(self) -> None:
        self.capture["closed"] = True


def preset(mode: CredentialMode) -> ProviderPreset:
    return ProviderPreset(
        id="compatible",
        label="Compatible",
        model_label="Allowed model",
        base_url="https://provider.example/v1",
        model="fixed-model",
        credential_mode=mode,
        server_api_key=SecretStr("server-secret")
        if mode is CredentialMode.SERVER_MANAGED
        else None,
    )


async def test_adapter_fixes_destination_roles_and_parameters() -> None:
    capture: dict[str, Any] = {}
    provider = OpenAICompatibleProvider(
        preset(CredentialMode.SERVER_MANAGED),
        timeout_seconds=17,
        client_factory=lambda **kwargs: FakeClient(capture, **kwargs),
    )

    result = await provider.complete(
        ProviderRequest(system_prompt="system", user_prompt="user", max_output_tokens=321)
    )

    assert capture["client"] == {
        "api_key": "server-secret",
        "base_url": "https://provider.example/v1",
        "timeout": 17,
        "max_retries": 0,
    }
    request = capture["request"]
    assert request["model"] == "fixed-model"
    assert request["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
    ]
    assert request["temperature"] == 0.2
    assert request["max_tokens"] == 321
    assert request["stream"] is False
    assert capture["closed"] is True
    assert result.text == "model output"
    assert result.input_tokens == 12
    assert result.output_tokens == 3


async def test_participant_key_is_required_and_request_scoped() -> None:
    capture: dict[str, Any] = {}
    provider = OpenAICompatibleProvider(
        preset(CredentialMode.PARTICIPANT_PROVIDED),
        timeout_seconds=10,
        client_factory=lambda **kwargs: FakeClient(capture, **kwargs),
    )

    with pytest.raises(ProviderCredentialRequiredError):
        await provider.complete(ProviderRequest("system", "user", 100))

    await provider.complete(
        ProviderRequest("system", "user", 100),
        participant_api_key=SecretStr("participant-secret"),
    )
    assert capture["client"]["api_key"] == "participant-secret"
    assert capture["closed"] is True
