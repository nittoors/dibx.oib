import pytest
from pydantic import ValidationError

from app.config import LOCAL_DATABASE_URL, Settings


@pytest.fixture(autouse=True)
def isolate_database_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("DATABASE_URL", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"):
        monkeypatch.delenv(name, raising=False)


def test_local_database_url_remains_the_default() -> None:
    assert Settings().database_url == LOCAL_DATABASE_URL


def test_database_url_is_built_from_aws_secret_components() -> None:
    settings = Settings(
        db_host="database.internal",
        db_port=5432,
        db_name="depot_readiness",
        db_user="depot_app",
        db_password="special:/?#[]@ value",
    )

    assert settings.database_url == (
        "postgresql+psycopg://depot_app:special%3A%2F%3F%23%5B%5D%40 value"
        "@database.internal:5432/depot_readiness"
    )


def test_production_database_components_require_tls() -> None:
    settings = Settings(
        app_env="production",
        auth_mode="cognito",
        db_host="database.internal",
        db_name="oib_readiness",
        db_user="depot_app",
        db_password="secret",
        cognito_issuer_url="https://cognito-idp.us-east-1.amazonaws.com/us-east-1_example",
        cognito_client_id="client",
    )

    assert settings.database_url.endswith("/oib_readiness?sslmode=require")


def test_explicit_database_url_takes_precedence_over_components() -> None:
    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        db_host="database.internal",
        db_user="depot_app",
        db_password="ignored",
    )

    assert settings.database_url == "sqlite+pysqlite:///:memory:"


def test_incomplete_database_components_fail_closed() -> None:
    with pytest.raises(ValidationError, match="DB_USER and DB_PASSWORD"):
        Settings(db_host="database.internal", db_user="depot_app")
