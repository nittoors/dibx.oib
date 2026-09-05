from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Provide one database session per request."""

    with SessionLocal() as session:
        yield session


def database_is_ready() -> bool:
    """Return whether the configured database accepts a minimal query."""

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:  # The readiness endpoint reports failure without leaking details.
        return False
    return True
