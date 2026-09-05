from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import auth
from app.auth import ADMIN_GROUP, ASSESSOR_GROUP, Principal
from app.config import Settings, get_settings
from app.main import app


def test_production_like_environments_fail_closed_without_cognito() -> None:
    with pytest.raises(ValidationError, match="AUTH_MODE must be cognito"):
        Settings(app_env="production", auth_mode="development")


def test_cognito_access_token_validates_client_type_roles_and_depots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    issuer = "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_example"
    settings = Settings(
        app_env="test",
        auth_mode="cognito",
        cognito_issuer_url=issuer,
        cognito_client_id="client-123",
        cognito_required_scope="oib/read",
    )
    token = jwt.encode(
        {
            "sub": "user-123",
            "iss": issuer,
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "client_id": "client-123",
            "token_use": "access",
            "scope": "openid oib/read",
            "cognito:groups": [ASSESSOR_GROUP],
            "custom:depots": "RRAD, ANAD,INVALID",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    monkeypatch.setattr(
        auth,
        "_jwks_client",
        lambda _issuer: SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=private_key.public_key())
        ),
    )

    principal = auth._verify_cognito_token(token, settings)

    assert principal.subject == "user-123"
    assert principal.groups == frozenset({ASSESSOR_GROUP})
    assert principal.depots == frozenset({"RRAD", "ANAD"})
    assert principal.can_assess()
    assert principal.can_access_depot("RRAD")
    assert not principal.can_access_depot("SIAD")

    wrong_use = jwt.encode(
        {
            "sub": "user-123",
            "iss": issuer,
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "client_id": "client-123",
            "token_use": "id",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    with pytest.raises(HTTPException) as error:
        auth._verify_cognito_token(wrong_use, settings)
    assert getattr(error.value, "status_code", None) == 401


def test_missing_bearer_token_is_rejected_in_cognito_mode() -> None:
    settings = Settings(
        app_env="test",
        auth_mode="cognito",
        cognito_issuer_url="https://cognito-idp.us-east-1.amazonaws.com/us-east-1_example",
        cognito_client_id="client-123",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        response = TestClient(app).get("/api/v1/session")
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_role_and_depot_helpers_enforce_server_scope() -> None:
    principal = Principal(
        subject="viewer",
        groups=frozenset({"OIB-Viewers"}),
        depots=frozenset({"RRAD"}),
        authentication_mode="cognito",
    )
    assert principal.can_read()
    assert not principal.can_assess()
    assert not principal.can_access_depot("ALL")
    assert Principal(
        subject="admin",
        groups=frozenset({ADMIN_GROUP}),
        depots=frozenset(),
        authentication_mode="cognito",
    ).can_access_depot("Other")
