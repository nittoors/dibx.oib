"""Create the OIB logical database on the shared PostgreSQL instance if absent."""

import os

import psycopg
from psycopg import sql


def main() -> None:
    host = os.environ["DB_HOST"]
    port = int(os.environ.get("DB_PORT", "5432"))
    user = os.environ["DB_USER"]
    password = os.environ["DB_PASSWORD"]
    database = os.environ.get("DB_NAME", "oib_readiness")
    maintenance_database = os.environ.get("DB_MAINTENANCE_NAME", "dbix")
    sslmode = os.environ.get("DB_SSLMODE", "require")

    with psycopg.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=maintenance_database,
        sslmode=sslmode,
        autocommit=True,
    ) as connection:
        exists = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (database,)
        ).fetchone()
        if exists is None:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
            print(f"Created logical database {database}")
        else:
            print(f"Logical database {database} already exists")


if __name__ == "__main__":
    main()
