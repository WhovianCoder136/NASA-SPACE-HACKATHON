"""Pytest fixtures for ASTRA-MED integration and unit tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from astra_med.db import crud
from astra_med.db.models import Base

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=TEST_ENGINE,
    expire_on_commit=False,
)


@pytest.fixture(scope="function")
def test_session() -> Generator[Session, None, None]:
    """Provide a fresh in-memory SQLite database session per test function."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture(scope="function")
def sample_crew(test_session: Session):
    """Seed sample crew member."""
    crew = crud.create_crew_member(
        session=test_session,
        name="CDR John Glenn",
        role="Commander",
        status="active",
    )
    test_session.commit()
    return crew
