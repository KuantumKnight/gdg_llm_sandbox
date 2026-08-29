from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AttemptRequest(BaseModel):
    model_config = {"extra": "forbid"}

    prompt: str = Field(min_length=1)

    @field_validator("prompt")
    @classmethod
    def reject_whitespace_only(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("prompt cannot be empty or whitespace")
        return value


class UsageData(BaseModel):
    input_tokens: int | None
    output_tokens: int | None


class AttemptData(BaseModel):
    attempt_id: str
    model_response: str
    solved: bool
    remaining_attempts: int
    provider_outcome: Literal["completed"] = "completed"
    usage: UsageData
    solved_at: datetime | None = None
    next_round_hint: str | None = None


class AttemptEnvelope(BaseModel):
    data: AttemptData
