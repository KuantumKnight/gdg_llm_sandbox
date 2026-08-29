"""Bounded OpenAI-compatible Chat Completions adapter."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, cast

import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import SecretStr

from app.core.config import CredentialMode, ProviderPreset
from app.domain.entities import CompletionResult
from app.providers.base import ProviderRequest
from app.providers.errors import (
    ProviderConfigurationError,
    ProviderCredentialRejectedError,
    ProviderCredentialRequiredError,
    ProviderError,
    ProviderMalformedResponseError,
    ProviderRateLimitedError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


class OpenAIClientLike(Protocol):
    chat: Any

    async def close(self) -> None: ...


ClientFactory = Callable[..., OpenAIClientLike]


class OpenAICompatibleProvider:
    """Use only the portable text subset of the OpenAI Chat Completions protocol."""

    def __init__(
        self,
        preset: ProviderPreset,
        *,
        timeout_seconds: float,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self.preset = preset
        self.timeout_seconds = timeout_seconds
        self.client_factory = client_factory or cast(ClientFactory, AsyncOpenAI)

    async def complete(
        self, request: ProviderRequest, *, participant_api_key: SecretStr | None = None
    ) -> CompletionResult:
        api_key = self._resolve_api_key(participant_api_key)
        client = self.client_factory(
            api_key=api_key,
            base_url=self.preset.base_url,
            timeout=self.timeout_seconds,
            max_retries=0,
        )
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.user_prompt},
        ]
        try:
            completion = await client.chat.completions.create(
                model=self.preset.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_output_tokens,
                stream=False,
            )
        except Exception as exc:
            raise map_openai_error(exc) from exc
        finally:
            await client.close()

        if not completion.choices:
            raise ProviderMalformedResponseError("provider returned no choices")
        content = completion.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise ProviderMalformedResponseError("provider returned no text")
        usage = completion.usage
        return CompletionResult(
            text=content,
            input_tokens=None if usage is None else usage.prompt_tokens,
            output_tokens=None if usage is None else usage.completion_tokens,
            provider_request_id=cast(str | None, getattr(completion, "_request_id", None)),
        )

    def _resolve_api_key(self, participant_api_key: SecretStr | None) -> str:
        if self.preset.credential_mode is CredentialMode.PARTICIPANT_PROVIDED:
            if participant_api_key is None or not participant_api_key.get_secret_value():
                raise ProviderCredentialRequiredError("participant provider key is required")
            return participant_api_key.get_secret_value()
        if self.preset.server_api_key is None:
            raise ProviderConfigurationError("server-managed provider key is missing")
        return self.preset.server_api_key.get_secret_value()


def map_openai_error(exc: Exception) -> ProviderError:
    """Normalize SDK details without forwarding upstream bodies or headers."""
    if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
        return ProviderCredentialRejectedError("provider rejected the credential")
    if isinstance(exc, openai.RateLimitError):
        return ProviderRateLimitedError("provider rate limit reached")
    if isinstance(exc, openai.APITimeoutError):
        return ProviderTimeoutError("provider response timed out")
    if isinstance(exc, (openai.BadRequestError, openai.NotFoundError)):
        return ProviderConfigurationError("provider preset is not accepted")
    if isinstance(exc, (openai.APIConnectionError, openai.APIStatusError)):
        return ProviderUnavailableError("provider request failed")
    if isinstance(exc, ProviderError):
        return exc
    return ProviderUnavailableError("unexpected provider failure")
