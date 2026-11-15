"""ASTRA-MED FastAPI Main Application Entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from astra_med.api import auth
from astra_med.api.deps import get_action_card_registry
from astra_med.api.routes import (
    action_cards,
    actions,
    alerts,
    astronauts,
    baselines,
    biosample,
    crew,
    ground_review,
    health_checkups,
    insights,
    measurements,
    medical_reports,
    ml_inference,
    vitals,
)
from astra_med.config import (
    API_V1_PREFIX,
    FRONTEND_DIR,
    PROJECT_DESCRIPTION,
    PROJECT_NAME,
    PROJECT_VERSION,
    STATIC_DIR,
)
from astra_med.db import crud
from astra_med.db.database import init_db, session_factory


import logging

logger = logging.getLogger("astra_med.startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    try:
        # 1. Initialize SQLite/PostgreSQL tables and run schema migrations
        init_db()

        # 2. Seed default Action Cards & initial crew members
        with session_factory() as session:
            registry = get_action_card_registry()
            registry.seed_defaults(session)

            members = crud.list_crew_members(session)
            if not members:
                c1 = crud.create_crew_member(
                    session=session,
                    name="CDR Sarah Chen, MD",
                    role="Mission Commander / Astrobiologist & Flight Medical Officer",
                    status="active",
                    astronaut_id="ASTRA-001",
                    mission_id="ASTRA-1",
                    username="chen",
                    password_hash=auth.get_password_hash("password123"),
                    is_medical_officer=True,
                )
                c2 = crud.create_crew_member(
                    session=session,
                    name="PLT Marcus Vance",
                    role="Pilot / Systems Engineer",
                    status="active",
                    astronaut_id="ASTRA-002",
                    mission_id="ASTRA-1",
                    username="vance",
                    password_hash=auth.get_password_hash("password123"),
                    is_medical_officer=False,
                )
                session.flush()
            else:
                c1 = crud.get_crew_by_astronaut_id(session, "ASTRA-001") or members[0]

            # Ensure initial checkup baseline exists for primary commander
            existing_chk = crud.get_health_checkup(session, "CHK-20261114-ASTRA001-INIT")
            if not existing_chk and c1:
                chk = crud.create_health_checkup(
                    session=session,
                    checkup_id="CHK-20261114-ASTRA001-INIT",
                    astronaut_id=c1.astronaut_id,
                    crew_id=c1.id,
                    checkup_date="2026-11-14",
                    checkup_time="08:30",
                    location="Mars Transit Hab — Clinical Station",
                    medical_officer="CDR Sarah Chen, MD",
                    checkup_type="Routine health checkup",
                    notes="Flight Day 141 baseline acclimatization assessment. Cardiovascular and sleep parameters nominal.",
                    submitted_by_crew_id=c1.id,
                    submitted_by_name=c1.name,
                    is_submitted_by_officer=True,
                )
                crud.add_checkup_measurement(session, chk.id, "basic", "heart_rate", 72.0, "bpm", "60 - 100")
                crud.add_checkup_measurement(session, chk.id, "basic", "bp_systolic", 118.0, "mmHg", "90 - 120")
                crud.add_checkup_measurement(session, chk.id, "basic", "bp_diastolic", 76.0, "mmHg", "60 - 80")
                crud.add_checkup_measurement(session, chk.id, "basic", "spo2", 98.5, "%", "95 - 100")
                crud.add_checkup_measurement(session, chk.id, "basic", "temperature", 36.6, "°C", "36.1 - 37.2")
            session.commit()
            logger.info("ASTRA-MED database startup and initialization nominal.")
    except Exception as exc:
        logger.error("ASTRA-MED startup initialization encountered an error: %s", exc, exc_info=True)
        raise

    yield


app = FastAPI(
    title=PROJECT_NAME,
    version=PROJECT_VERSION,
    description=PROJECT_DESCRIPTION,
    lifespan=lifespan,
)

# CORS Middleware (allows offline web UI connections)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers under /api/v1 (Existing standard)
app.include_router(auth.router, prefix=API_V1_PREFIX)
app.include_router(health_checkups.router, prefix=API_V1_PREFIX)
app.include_router(crew.router, prefix=API_V1_PREFIX)
app.include_router(vitals.router, prefix=API_V1_PREFIX)
app.include_router(alerts.router, prefix=API_V1_PREFIX)
app.include_router(action_cards.router, prefix=API_V1_PREFIX)
app.include_router(baselines.router, prefix=API_V1_PREFIX)
app.include_router(biosample.router, prefix=API_V1_PREFIX)
app.include_router(ground_review.router, prefix=API_V1_PREFIX)
app.include_router(ml_inference.router, prefix=API_V1_PREFIX)
app.include_router(insights.router, prefix=API_V1_PREFIX)
app.include_router(actions.router, prefix=API_V1_PREFIX)
app.include_router(medical_reports.router, prefix=API_V1_PREFIX)
app.include_router(measurements.router, prefix=API_V1_PREFIX)
app.include_router(astronauts.router, prefix=API_V1_PREFIX)

# Also Mount API Routers under /api (Direct contract alignment with Handoff Spec)
app.include_router(auth.router, prefix="/api")
app.include_router(health_checkups.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(actions.router, prefix="/api")
app.include_router(medical_reports.router, prefix="/api")
app.include_router(measurements.router, prefix="/api")
app.include_router(astronauts.router, prefix="/api")
app.include_router(ml_inference.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")


@app.get("/api/health", tags=["System"])
@app.get(f"{API_V1_PREFIX}/status", tags=["System"])
@app.get("/health", tags=["System"])
def system_status():
    """System health check and operational status."""
    return {
        "status": "nominal",
        "system": PROJECT_NAME,
        "version": PROJECT_VERSION,
        "mode": "autonomous_offline",
        "comms_latency_minutes": 20.0,
        "security_policy": "no_autonomous_diagnosis_no_unapproved_pharmacology",
    }


system_health_status = system_status


@app.get("/api/sync/status", tags=["Store & Forward"])
@app.get(f"{API_V1_PREFIX}/sync/status", tags=["Store & Forward"])
def sync_status():
    """Status of Earth store-and-forward communication link."""
    with session_factory() as session:
        pending_enc = crud.get_pending_encounters(session)
        pending_rep = crud.get_medical_reports_for_crew(session, status="queued_for_sync")
        return {
            "link_status": "offline_buffered",
            "one_way_latency_minutes": 20.0,
            "pending_encounters": len(pending_enc),
            "pending_medical_reports": len(pending_rep),
            "encryption": "AES-256-GCM / SHA-256",
            "next_scheduled_downlink_window_met": 142.5,
        }


@app.get("/api/sync/queue", tags=["Store & Forward"])
@app.get(f"{API_V1_PREFIX}/sync/queue", tags=["Store & Forward"])
def get_sync_queue():
    """Get all queued telemetry and medical reports awaiting Earth sync."""
    with session_factory() as session:
        encs = crud.get_pending_encounters(session)
        reps = crud.get_medical_reports_for_crew(session, status="queued_for_sync")
        return {
            "encounters": [
                {
                    "id": e.id,
                    "uuid": e.encounter_uuid,
                    "crew_id": e.crew_id,
                    "checksum": e.checksum,
                    "timestamp_met": e.timestamp_met,
                }
                for e in encs
            ],
            "reports": [
                {
                    "id": r.id,
                    "report_id": r.report_id,
                    "crew_id": r.crew_id,
                    "title": r.title,
                    "domain": r.domain,
                    "checksum": r.checksum,
                }
                for r in reps
            ],
        }


# Mount Frontend Static Assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def serve_index():
    """Serve the ASTRA-MED Single Page Application."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "ASTRA-MED API Online. Frontend index.html not found."}
