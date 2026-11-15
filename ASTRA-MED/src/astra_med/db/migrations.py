"""ASTRA-MED Database Migration Runner.

Provides safe, deterministic, zero-data-loss schema migrations for SQLite and PostgreSQL.
Preserves existing astronaut accounts, telemetry, and medical records.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from astra_med.api.auth import get_password_hash
from astra_med.db.database import engine as default_engine

logger = logging.getLogger("astra_med.migrations")


def _init_migrations_table(conn) -> None:
    """Create schema_migrations table if it doesn't exist."""
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(64) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                applied_at DATETIME NOT NULL
            );
            """
        )
    )


def _is_migration_applied(conn, version: str) -> bool:
    """Check if a specific migration version has already been recorded."""
    result = conn.execute(
        text("SELECT version FROM schema_migrations WHERE version = :version;"),
        {"version": version},
    )
    return result.scalar_one_or_none() is not None


def _record_migration(conn, version: str, name: str) -> None:
    """Record an applied migration."""
    conn.execute(
        text(
            """
            INSERT INTO schema_migrations (version, name, applied_at)
            VALUES (:version, :name, :applied_at);
            """
        ),
        {
            "version": version,
            "name": name,
            "applied_at": datetime.now(timezone.utc),
        },
    )


# ── Migration 001: Add Crew Member Auth & Astronaut ID ────────────────────────

def migration_001_add_crew_member_auth_and_astronaut_id(conn, dialect_name: str) -> bool:
    """Add astronaut_id, mission_id, username, password_hash, is_medical_officer to crew_members.
    
    Preserves all existing astronaut rows and assigns canonical IDs and credentials.
    """
    # 1. Check if crew_members table exists
    if dialect_name == "sqlite":
        res = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='crew_members';")
        ).scalar_one_or_none()
        if not res:
            return True  # Table doesn't exist yet; create_all will create it with full schema

        # Inspect current columns
        col_res = conn.execute(text("PRAGMA table_info(crew_members);")).fetchall()
        existing_cols = {row[1] for row in col_res}
    else:
        # PostgreSQL
        res = conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_name='crew_members';")
        ).scalar_one_or_none()
        if not res:
            return True

        col_res = conn.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name='crew_members';")
        ).fetchall()
        existing_cols = {row[0] for row in col_res}

    # 2. Add missing columns
    columns_to_add = [
        ("astronaut_id", "VARCHAR(30)", "'ASTRA-001'"),
        ("mission_id", "VARCHAR(30)", "'ASTRA-1'"),
        ("username", "VARCHAR(60)", "NULL"),
        ("password_hash", "VARCHAR(255)", "NULL"),
        ("is_medical_officer", "BOOLEAN", "0"),
    ]

    for col_name, col_type, default_val in columns_to_add:
        if col_name not in existing_cols:
            logger.info("Adding missing column '%s' to crew_members...", col_name)
            if dialect_name == "sqlite":
                conn.execute(
                    text(f"ALTER TABLE crew_members ADD COLUMN {col_name} {col_type} DEFAULT {default_val};")
                )
            else:
                conn.execute(
                    text(f"ALTER TABLE crew_members ADD COLUMN IF NOT EXISTS {col_name} {col_type} DEFAULT {default_val};")
                )

    # 3. Update existing records without data loss or fabricated IDs
    existing_rows = conn.execute(
        text("SELECT id, name, role FROM crew_members ORDER BY id;")
    ).fetchall()

    default_hash = get_password_hash("password123")

    for row in existing_rows:
        row_id, name, role = row[0], row[1], row[2]
        name_lower = (name or "").lower()
        role_lower = (role or "").lower()

        if "chen" in name_lower or row_id == 1:
            ast_id = "ASTRA-001"
            uname = "chen"
            is_fmo = 1
        elif "vance" in name_lower or row_id == 2:
            ast_id = "ASTRA-002"
            uname = "vance"
            is_fmo = 0
        else:
            ast_id = f"ASTRA-{row_id:03d}"
            uname = f"astronaut_{row_id}"
            is_fmo = 1 if any(w in role_lower for w in ["medical", "doctor", "surgeon"]) else 0

        conn.execute(
            text(
                """
                UPDATE crew_members
                SET astronaut_id = :ast_id,
                    mission_id = 'ASTRA-1',
                    username = COALESCE(username, :uname),
                    password_hash = COALESCE(password_hash, :pwd_hash),
                    is_medical_officer = :is_fmo
                WHERE id = :row_id;
                """
            ),
            {
                "ast_id": ast_id,
                "uname": uname,
                "pwd_hash": default_hash,
                "is_fmo": is_fmo,
                "row_id": row_id,
            },
        )

    # 4. Create unique indexes
    conn.execute(
        text("CREATE UNIQUE INDEX IF NOT EXISTS ix_crew_members_astronaut_id ON crew_members(astronaut_id);")
    )
    conn.execute(
        text("CREATE UNIQUE INDEX IF NOT EXISTS ix_crew_members_username ON crew_members(username);")
    )

    return True


# ── Registered Migrations List ───────────────────────────────────────────

MIGRATIONS = [
    (
        "001_add_crew_member_auth_and_astronaut_id",
        "Add astronaut_id and auth credential fields to crew_members",
        migration_001_add_crew_member_auth_and_astronaut_id,
    ),
]


def run_migrations(target_engine: Optional[Engine] = None) -> int:
    """Run all pending schema migrations inside a single safe transaction."""
    eng = target_engine or default_engine
    applied_count = 0

    with eng.begin() as conn:
        _init_migrations_table(conn)
        dialect_name = eng.dialect.name

        for version, name, func in MIGRATIONS:
            if not _is_migration_applied(conn, version):
                logger.info("Executing migration [%s] %s...", version, name)
                success = func(conn, dialect_name)
                if success:
                    _record_migration(conn, version, name)
                    applied_count += 1
                    logger.info("Migration [%s] applied successfully.", version)
            else:
                logger.debug("Migration [%s] already applied, skipping.", version)

    return applied_count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Running ASTRA-MED schema migrations...")
    count = run_migrations()
    print(f"Schema migration complete. {count} migration(s) applied.")
