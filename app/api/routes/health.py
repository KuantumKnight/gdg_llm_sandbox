from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.dependencies import RepositoryDep
from app.domain.errors import StateUnavailableError

router = APIRouter(tags=["operations"])


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "live"}


@router.get("/health/ready")
async def readiness(request: Request, repository: RepositoryDep) -> JSONResponse:
    try:
        ready = await repository.ping()
    except StateUnavailableError:
        ready = False
    status = 200 if ready else 503
    return JSONResponse(
        status_code=status,
        content={"status": "ready" if ready else "not_ready", "dependencies": {"state": ready}},
        headers={"X-Request-ID": request.state.request_id},
    )
