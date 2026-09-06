from functools import lru_cache
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

LOCAL_DATABASE_URL = (
    "postgresql+psycopg://depot_app:local-development-only@localhost:5432/depot_readiness"
)


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Depot Readiness API"
    app_version: str = "0.1.0"
    app_env: str = "local"
    auth_mode: Literal["development", "public_readonly", "cognito"] = "development"
    database_url: str = LOCAL_DATABASE_URL
    db_host: str | None = None
    db_port: int = 5432
    db_name: str = "depot_readiness"
    db_user: str | None = None
    db_password: SecretStr | None = None
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    cognito_issuer_url: str | None = None
    cognito_client_id: str | None = None
    cognito_required_scope: str | None = None
    cognito_depot_claim: str = "custom:depots"
    development_subject: str = "local-reviewer"

    @property
    def is_production_like(self) -> bool:
        return self.app_env.lower() not in {"local", "test", "development"}

    @model_validator(mode="after")
    def validate_runtime_configuration(self) -> Self:
        database_url_was_supplied = "database_url" in self.model_fields_set
        if self.db_host and not database_url_was_supplied:
            if not self.db_user or not self.db_password:
                raise ValueError("DB_USER and DB_PASSWORD are required when DB_HOST is configured")
            self.database_url = URL.create(
                drivername="postgresql+psycopg",
                username=self.db_user,
                password=self.db_password.get_secret_value(),
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                query={"sslmode": "require"} if self.is_production_like else {},
            ).render_as_string(hide_password=False)
        if self.is_production_like and self.auth_mode not in {"cognito", "public_readonly"}:
            raise ValueError(
                "AUTH_MODE must be cognito or public_readonly outside local/test/development"
            )
        if self.auth_mode == "cognito":
            if not self.cognito_issuer_url or not self.cognito_client_id:
                raise ValueError(
                    "COGNITO_ISSUER_URL and COGNITO_CLIENT_ID are required in cognito mode"
                )
            issuer = urlsplit(self.cognito_issuer_url)
            hostname = issuer.hostname or ""
            valid_hostname = hostname.startswith("cognito-idp.") and (
                hostname.endswith(".amazonaws.com") or hostname.endswith(".amazonaws.com.cn")
            )
            if (
                issuer.scheme != "https"
                or not valid_hostname
                or not issuer.path.strip("/")
                or issuer.username
                or issuer.password
                or issuer.port
                or issuer.query
                or issuer.fragment
            ):
                raise ValueError("COGNITO_ISSUER_URL must be an HTTPS Amazon Cognito issuer")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
