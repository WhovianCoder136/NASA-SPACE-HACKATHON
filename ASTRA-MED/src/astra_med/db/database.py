"""SQLAlchemy engine, session factory, and DB lifecycle helpers (offline-safe)."""

from __future__ import annotations

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from astra_med.config import DATABASE_URL, DATA_DIR, MEDICAL_FILES_DIR, UPLOADS_DIR

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

session_factory = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    with session_factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


_db_initialized = False


def init_db() -> None:
    """Run pending schema migrations and create all tables (idempotent)."""
    global _db_initialized
    if _db_initialized:
        return

    from astra_med.db.models import Base
    from astra_med.db.migrations import run_migrations

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    MEDICAL_FILES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Run migrations on existing schema to prevent missing-column errors
    run_migrations(engine)

    # 2. Ensure any new tables are created
    Base.metadata.create_all(bind=engine)
    _db_initialized = True
