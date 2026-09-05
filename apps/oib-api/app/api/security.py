from fastapi import APIRouter

from app.api.contracts import SessionResponse
from app.auth import CurrentViewer

router = APIRouter(tags=["security"])


@router.get("/session", response_model=SessionResponse)
def session(principal: CurrentViewer) -> SessionResponse:
    return SessionResponse(
        subject=principal.subject,
        roles=sorted(principal.groups),
        allowed_depots=sorted(principal.depots),
        authentication_mode=principal.authentication_mode,
    )
