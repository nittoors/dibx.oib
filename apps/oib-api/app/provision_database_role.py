"""Provision the least-privilege PostgreSQL role used by the long-running OIB API."""

from __future__ import annotations

import os

import psycopg
from psycopg import sql


def main() -> None:
    host = os.environ["DB_HOST"]
    port = int(os.environ.get("DB_PORT", "5432"))
    database = os.environ.get("DB_NAME", "oib_readiness")
    admin_user = os.environ["DB_USER"]
    admin_password = os.environ["DB_PASSWORD"]
    application_user = os.environ["APP_DB_USER"]
    application_password = os.environ["APP_DB_PASSWORD"]

    with psycopg.connect(
        host=host,
        port=port,
        dbname=database,
        user=admin_user,
        password=admin_password,
        sslmode=os.environ.get("DB_SSLMODE", "require"),
        autocommit=True,
    ) as connection:
        exists = connection.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s", (application_user,)
        ).fetchone()
        password_literal = sql.Literal(application_password)
        role_identifier = sql.Identifier(application_user)
        if exists is None:
            connection.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB "
                    "NOCREATEROLE NOINHERIT NOREPLICATION"
                ).format(role_identifier, password_literal)
            )
        else:
            connection.execute(
                sql.SQL(
                    "ALTER ROLE {} WITH LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB "
                    "NOCREATEROLE NOINHERIT NOREPLICATION"
                ).format(role_identifier, password_literal)
            )

        database_identifier = sql.Identifier(database)
        statements: list[sql.SQL | sql.Composed] = [
            sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(database_identifier),
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                database_identifier, role_identifier
            ),
            sql.SQL("REVOKE CREATE ON SCHEMA public FROM PUBLIC"),
            sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role_identifier),
            sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(
                role_identifier
            ),
            sql.SQL("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {}").format(
                role_identifier
            ),
            sql.SQL(
                "GRANT INSERT ON TABLE public.submitted_connectivity_assessments, "
                "public.audit_events TO {}"
            ).format(role_identifier),
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {}"
            ).format(role_identifier),
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                "GRANT USAGE, SELECT ON SEQUENCES TO {}"
            ).format(role_identifier),
        ]
        for statement in statements:
            connection.execute(statement)

    print(f"Provisioned least-privilege OIB database role {application_user}")


if __name__ == "__main__":
    main()
