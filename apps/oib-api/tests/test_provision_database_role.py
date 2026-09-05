from __future__ import annotations

from typing import Any

import pytest

from app import provision_database_role


class FakeResult:
    def __init__(self, role_exists: bool) -> None:
        self.role_exists = role_exists

    def fetchone(self) -> tuple[int] | None:
        return (1,) if self.role_exists else None


class FakeConnection:
    def __init__(self, role_exists: bool) -> None:
        self.role_exists = role_exists
        self.calls: list[tuple[Any, object | None]] = []

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, statement: Any, parameters: object | None = None) -> FakeResult:
        self.calls.append((statement, parameters))
        return FakeResult(self.role_exists if len(self.calls) == 1 else False)


@pytest.mark.parametrize("role_exists", [False, True])
def test_provision_database_role_is_idempotent_and_uses_tls(
    monkeypatch: pytest.MonkeyPatch, role_exists: bool
) -> None:
    connection = FakeConnection(role_exists)
    connection_options: dict[str, object] = {}
    monkeypatch.setenv("DB_HOST", "database.internal")
    monkeypatch.setenv("DB_NAME", "oib_readiness")
    monkeypatch.setenv("DB_USER", "dbix_admin")
    monkeypatch.setenv("DB_PASSWORD", "admin-secret")
    monkeypatch.setenv("APP_DB_USER", "dbix_oib_app")
    monkeypatch.setenv("APP_DB_PASSWORD", "application-secret")

    def connect(**options: object) -> FakeConnection:
        connection_options.update(options)
        return connection

    monkeypatch.setattr("app.provision_database_role.psycopg.connect", connect)

    provision_database_role.main()

    assert connection_options == {
        "host": "database.internal",
        "port": 5432,
        "dbname": "oib_readiness",
        "user": "dbix_admin",
        "password": "admin-secret",
        "sslmode": "require",
        "autocommit": True,
    }
    assert len(connection.calls) == 11
    assert connection.calls[0][1] == ("dbix_oib_app",)
