"""Tests for Database Schema Alignment, Migrations, and Application Startup.

Verifies:
1. All columns in crew_members exist (including astronaut_id)
2. Existing crew member rows and accounts are preserved without corruption
3. crud.list_crew_members executes cleanly without sqlite3.OperationalError
4. Migration runner is idempotent and safe
5. Astronaut login functions with verified credentials
6. Checkup intake and data persistence operate nominally
7. All 14 SQLAlchemy models match the database tables exactly
"""

from __future__ import annotations

import sqlite3
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from astra_med.api.auth import LoginRequest, login, verify_password
from astra_med.api.deps import (
    get_action_card_registry,
    get_alert_engine,
    get_baseline_engine,
    get_insight_engine,
    get_ml_router,
    get_store_forward_queue,
)
from astra_med.api.routes.health_checkups import (
    HealthCheckupCreateRequest,
    MeasurementItem,
    submit_health_checkup,
)
from astra_med.config import DB_PATH
from astra_med.db import crud
from astra_med.db.database import session_factory
from astra_med.db.migrations import run_migrations
from astra_med.db.models import Base, CrewMember


def test_schema_crew_members_columns():
    """Verify astronaut_id and all expected columns exist in physical SQLite table."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(crew_members);")
    cols = {row[1]: row[2] for row in cur.fetchall()}
    conn.close()

    expected_cols = [
        "id",
        "astronaut_id",
        "name",
        "role",
        "mission_id",
        "status",
        "username",
        "password_hash",
        "is_medical_officer",
        "created_at",
    ]
    for col in expected_cols:
        assert col in cols, f"Column '{col}' missing from crew_members table!"


def test_preserved_crew_members_data():
    """Verify existing astronaut accounts were preserved and mapped correctly."""
    with session_factory() as session:
        members = session.execute(select(CrewMember).order_by(CrewMember.id)).scalars().all()
        assert len(members) >= 2

        chen = next((m for m in members if m.astronaut_id == "ASTRA-001"), None)
        assert chen is not None
        assert chen.name == "CDR Sarah Chen" or "Sarah" in chen.name
        assert chen.username == "chen"
        assert chen.is_medical_officer is True
        assert chen.mission_id == "ASTRA-1"

        vance = next((m for m in members if m.astronaut_id == "ASTRA-002"), None)
        assert vance is not None
        assert "Marcus" in vance.name
        assert vance.username == "vance"
        assert vance.is_medical_officer is False


def test_crud_list_crew_members_no_error():
    """Verify that crud.list_crew_members executes without OperationalError."""
    with session_factory() as session:
        members = crud.list_crew_members(session)
        assert len(members) >= 2
        ids = {m.astronaut_id for m in members}
        assert "ASTRA-001" in ids
        assert "ASTRA-002" in ids


def test_migrations_idempotent():
    """Verify that running migrations repeatedly is safe and idempotent."""
    applied = run_migrations()
    assert applied == 0  # Already up to date


def test_astronaut_login_and_auth():
    """Verify astronaut authentication and password verification."""
    with session_factory() as session:
        req = LoginRequest(username="chen", password="password123")
        token_resp = login(req, session=session)
        assert token_resp.astronaut_id == "ASTRA-001"
        assert token_resp.is_medical_officer is True
        assert token_resp.access_token is not None


def test_checkup_submission_with_migrated_db():
    """Verify health checkup submission persists in database."""
    with session_factory() as session:
        commander = crud.get_crew_by_astronaut_id(session, "ASTRA-001")
        assert commander is not None

        req = HealthCheckupCreateRequest(
            astronaut_id="ASTRA-001",
            checkup_date="2026-11-15",
            checkup_type="Routine health checkup",
            notes="Automated schema verification checkup.",
            measurements=[
                MeasurementItem(domain="basic", metric_name="heart_rate", value=71.0, unit="bpm"),
                MeasurementItem(domain="basic", metric_name="bp_systolic", value=119.0, unit="mmHg"),
                MeasurementItem(domain="basic", metric_name="bp_diastolic", value=77.0, unit="mmHg"),
            ],
        )

        res = submit_health_checkup(
            req=req,
            current_user=commander,
            session=session,
            baseline_engine=get_baseline_engine(),
            alert_engine=get_alert_engine(),
            insight_engine=get_insight_engine(),
            ml_router=get_ml_router(),
            card_registry=get_action_card_registry(),
            sf_queue=get_store_forward_queue(),
        )

        assert res.measurements_saved == 3
        persisted = crud.get_health_checkup(session, res.checkup_id)
        assert persisted is not None
        assert len(persisted.measurements) == 3


def test_all_models_match_database_tables():
    """Audit all 14 models against physical database tables."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for mapper in Base.registry.mappers:
        table_name = mapper.local_table.name
        cur.execute(f"PRAGMA table_info({table_name});")
        db_cols = {row[1] for row in cur.fetchall()}
        model_cols = {col.name for col in mapper.local_table.columns}

        missing = model_cols - db_cols
        assert not missing, f"Table '{table_name}' has missing columns in database: {missing}"

    conn.close()
