"""Narrow provider port used by the attempt orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import SecretStr

from app.domain.entities import CompletionResult


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    system_prompt: str
    user_prompt: str
    max_output_tokens: int
    temperature: float = 0.2


class LLMProvider(Protocol):
    async def complete(
        self, request: ProviderRequest, *, participant_api_key: SecretStr | None = None
    ) -> CompletionResult: ...
