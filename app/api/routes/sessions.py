from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Header, Request, status

from app.api.dependencies import BearerDep, SessionServiceDep, SettingsDep
from app.schemas.sessions import (
    CreateSessionRequest,
    SessionData,
    SessionEnvelope,
)

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.post("", response_model=SessionEnvelope, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: CreateSessionRequest,
    request: Request,
    service: SessionServiceDep,
    round_code: Annotated[str, Header(alias="X-Round-Code")],
) -> SessionEnvelope:
    created = await service.create_session(
        round_code=round_code,
        preset_id=payload.preset_id,
        client_ip=request.client.host if request.client else "unknown",
        now=datetime.now(UTC),
    )
    return SessionEnvelope(
        data=SessionData.from_record(
            created.record,
            model_label=created.preset.model_label,
            credential_mode=created.preset.credential_mode,
            session_token=created.credentials.bearer_token,
        )
    )


@router.get("/{session_id}", response_model=SessionEnvelope)
async def get_session(
    session_id: str,
    bearer: BearerDep,
    service: SessionServiceDep,
    settings: SettingsDep,
) -> SessionEnvelope:
    record, preset = await service.authenticate(
        session_id=session_id, bearer_token=bearer, now=datetime.now(UTC)
    )
    return SessionEnvelope(
        data=SessionData.from_record(
            record,
            model_label=preset.model_label,
            credential_mode=preset.credential_mode,
            next_round_hint=(
                settings.next_round_hint.get_secret_value() if record.solved_at else None
            ),
        )
    )
