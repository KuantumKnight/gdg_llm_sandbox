from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Request
from pydantic import SecretStr

from app.api.dependencies import AttemptServiceDep, BearerDep
from app.schemas.attempts import AttemptEnvelope, AttemptRequest

router = APIRouter(prefix="/api/v1/sessions", tags=["attempts"])


@router.post("/{session_id}/attempts", response_model=AttemptEnvelope)
async def submit_attempt(
    session_id: str,
    payload: AttemptRequest,
    request: Request,
    bearer: BearerDep,
    service: AttemptServiceDep,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
    provider_api_key: Annotated[str | None, Header(alias="X-Provider-API-Key")] = None,
) -> AttemptEnvelope:
    data = await service.submit(
        session_id=session_id,
        bearer_token=bearer,
        idempotency_key=str(idempotency_key),
        prompt=payload.prompt,
        participant_api_key=SecretStr(provider_api_key) if provider_api_key else None,
        request_id=request.state.request_id,
    )
    return AttemptEnvelope(data=data)
