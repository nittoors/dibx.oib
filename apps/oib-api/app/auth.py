from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any, Literal

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError, PyJWKClient
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.config import Settings, get_settings

VIEWER_GROUP = "OIB-Viewers"
ASSESSOR_GROUP = "OIB-Assessors"
ADMIN_GROUP = "OIB-Admins"
KNOWN_GROUPS = frozenset({VIEWER_GROUP, ASSESSOR_GROUP, ADMIN_GROUP})
OPERATIONAL_DEPOTS = frozenset({"RRAD", "ANAD", "SIAD", "WVA"})
ALL_DEPOTS = OPERATIONAL_DEPOTS | {"Other"}


@dataclass(frozen=True)
class Principal:
    subject: str
    groups: frozenset[str]
    depots: frozenset[str]
    authentication_mode: Literal["development", "public_readonly", "cognito"]

    @property
    def is_admin(self) -> bool:
        return ADMIN_GROUP in self.groups

    def can_read(self) -> bool:
        return bool(self.groups & KNOWN_GROUPS)

    def can_assess(self) -> bool:
        return self.is_admin or ASSESSOR_GROUP in self.groups

    def can_access_depot(self, depot: str) -> bool:
        if self.is_admin:
            return True
        if depot == "ALL":
            return OPERATIONAL_DEPOTS.issubset(self.depots)
        return depot in self.depots


class CognitoClaims(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    sub: str = Field(min_length=1, max_length=256)
    client_id: str = Field(min_length=1, max_length=256)
    token_use: str
    scope: str = ""
    cognito_groups: list[str] = Field(default_factory=list, alias="cognito:groups")


bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=8)
def _jwks_client(issuer: str) -> PyJWKClient:
    return PyJWKClient(
        f"{issuer.rstrip('/')}/.well-known/jwks.json",
        cache_keys=True,
        timeout=5,
    )


def _unauthorized(detail: str = "Authentication is required") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _claim_depots(raw: Any) -> frozenset[str]:
    if isinstance(raw, str):
        values = raw.split(",")
    elif isinstance(raw, list) and all(isinstance(value, str) for value in raw):
        values = raw
    else:
        values = []
    return frozenset(value.strip() for value in values if value.strip() in ALL_DEPOTS)


def _verify_cognito_token(token: str, settings: Settings) -> Principal:
    if len(token) > 16_384:
        raise _unauthorized("Invalid access token")
    assert settings.cognito_issuer_url is not None
    assert settings.cognito_client_id is not None
    issuer = settings.cognito_issuer_url.rstrip("/")
    try:
        signing_key = _jwks_client(issuer).get_signing_key_from_jwt(token)
        raw_claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            options={
                "verify_aud": False,
                "require": ["sub", "exp", "iss", "client_id", "token_use"],
            },
        )
        claims = CognitoClaims.model_validate(raw_claims)
    except (InvalidTokenError, ValidationError, ValueError, TypeError) as error:
        raise _unauthorized("Invalid access token") from error
    if claims.token_use != "access" or claims.client_id != settings.cognito_client_id:
        raise _unauthorized("Invalid access token")
    if settings.cognito_required_scope:
        granted_scopes = frozenset(claims.scope.split())
        if settings.cognito_required_scope not in granted_scopes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    groups = frozenset(group for group in claims.cognito_groups if group in KNOWN_GROUPS)
    return Principal(
        subject=claims.sub,
        groups=groups,
        depots=_claim_depots(raw_claims.get(settings.cognito_depot_claim)),
        authentication_mode="cognito",
    )


def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Principal:
    if settings.auth_mode == "public_readonly":
        return Principal(
            subject="public-viewer",
            groups=frozenset({VIEWER_GROUP}),
            depots=ALL_DEPOTS,
            authentication_mode="public_readonly",
        )
    if settings.auth_mode == "development":
        if settings.is_production_like:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication is not configured",
            )
        return Principal(
            subject=settings.development_subject,
            groups=frozenset({ADMIN_GROUP}),
            depots=ALL_DEPOTS,
            authentication_mode="development",
        )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    return _verify_cognito_token(credentials.credentials, settings)


def require_viewer(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> Principal:
    if not principal.can_read():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewer role required")
    return principal


def require_assessor(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> Principal:
    if not principal.can_assess():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Assessor role required")
    return principal


def require_admin(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> Principal:
    if not principal.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required"
        )
    return principal


CurrentViewer = Annotated[Principal, Depends(require_viewer)]
CurrentAssessor = Annotated[Principal, Depends(require_assessor)]
CurrentAdmin = Annotated[Principal, Depends(require_admin)]


def authorize_depot(principal: Principal, depot: str) -> None:
    if not principal.can_access_depot(depot):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Depot access denied")
