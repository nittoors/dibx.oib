import re
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.assessments import router as assessment_router
from app.api.health import router as health_router
from app.api.read import router as read_router
from app.api.security import router as security_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url=None if settings.is_production_like else "/api/docs",
    redoc_url=None,
    openapi_url=None if settings.is_production_like else "/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Content-Type",
        "Authorization",
        "Idempotency-Key",
        "X-Request-ID",
    ],
)

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,128}$")


@app.middleware("http")
async def security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
    supplied_request_id = request.headers.get("X-Request-ID", "")
    request.state.request_id = (
        supplied_request_id if REQUEST_ID_PATTERN.fullmatch(supplied_request_id) else str(uuid4())
    )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response

app.include_router(health_router, prefix="/api/v1")
app.include_router(security_router, prefix="/api/v1")
app.include_router(read_router, prefix="/api/v1")
app.include_router(assessment_router, prefix="/api/v1")
