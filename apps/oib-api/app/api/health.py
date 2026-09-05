from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import get_settings
from app.db import database_is_ready

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str


@router.get("/live", response_model=HealthResponse)
def liveness() -> HealthResponse:
    """Report that the API process can handle requests."""

    settings = get_settings()
    return HealthResponse(status="ok", version=settings.app_version)


@router.get("/ready", response_model=HealthResponse)
def readiness() -> HealthResponse:
    """Report that the API and its PostgreSQL dependency are ready."""

    if not database_is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not ready",
        )
    settings = get_settings()
    return HealthResponse(status="ok", version=settings.app_version)
