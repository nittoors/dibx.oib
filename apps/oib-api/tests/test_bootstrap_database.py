from typing import Any

import pytest

from app import bootstrap_database


class FakeResult:
    def __init__(self, value: tuple[int] | None) -> None:
        self.value = value

    def fetchone(self) -> tuple[int] | None:
        return self.value


class FakeConnection:
    def __init__(self, database_exists: bool) -> None:
        self.database_exists = database_exists
        self.calls: list[tuple[Any, Any]] = []

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, statement: Any, parameters: Any = None) -> FakeResult:
        self.calls.append((statement, parameters))
        return FakeResult((1,) if self.database_exists else None)


@pytest.mark.parametrize(("database_exists", "expected_calls"), [(True, 1), (False, 2)])
def test_bootstrap_database_is_idempotent(
    monkeypatch: pytest.MonkeyPatch, database_exists: bool, expected_calls: int
) -> None:
    connection = FakeConnection(database_exists)
    monkeypatch.setenv("DB_HOST", "database.internal")
    monkeypatch.setenv("DB_USER", "dbix_admin")
    monkeypatch.setenv("DB_PASSWORD", "secret")
    monkeypatch.setattr("app.bootstrap_database.psycopg.connect", lambda **_aardvark: connection)

    bootstrap_database.main()

    assert len(connection.calls) == expected_calls
    assert connection.calls[0][1] == ("oib_readiness",)
