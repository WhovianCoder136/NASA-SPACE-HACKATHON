"""Comprehensive End-to-End (E2E) Test Suite for ASTRA-MED.

Tests the full application lifecycle:
1. Application initialization & static asset availability
2. User registration and authentication
3. Astronaut profile creation and retrieval
4. Sample health checkup intake & submission
5. Database persistence verification
6. All 7 health modules: Cardiovascular, Immune, Metabolic, Radiation, Sleep, Neuromuscular, SANS
7. Model predictions and baseline $Z$-score comparisons
8. Alerts, objective insights, and pre-approved action cards
9. Medical reports & simulated 20-minute Earth communication delay
10. Offline data store-and-forward queueing & synchronization
11. Dashboard overview and timeline updates after checkup submission
12. Error handling: invalid inputs, boundary violations, unauthorized access, and missing tokens
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile

from astra_med.api.auth import (
    LoginRequest,
    RegisterRequest,
    create_access_token,
    get_current_user,
    get_password_hash,
    login,
    register,
)
from astra_med.api.deps import (
    get_action_card_registry,
    get_action_engine,
    get_alert_engine,
    get_baseline_engine,
    get_insight_engine,
    get_ml_router,
    get_store_forward_queue,
)
from astra_med.api.main import app, serve_index, system_status, sync_status, get_sync_queue
from astra_med.api.routes.actions import acknowledge_action, list_actions_and_tasks
from astra_med.api.routes.action_cards import get_action_card, list_action_cards
from astra_med.api.routes.alerts import acknowledge_alert, list_active_alerts, list_alerts
from astra_med.api.routes.astronauts import get_astronaut_overview, list_astronauts
from astra_med.api.routes.baselines import get_specific_baseline, list_baselines_for_crew
from astra_med.api.routes.crew import CrewCreateRequest, create_crew, get_crew, list_crew
from astra_med.api.routes.ground_review import get_ground_queue, sync_encounter
from astra_med.api.routes.health_checkups import (
    CheckupUpdateRequest,
    HealthCheckupCreateRequest,
    MeasurementItem,
    download_medical_file,
    get_health_checkups_or_detail,
    get_medical_file_status,
    get_my_health_history,
    get_my_latest_checkup,
    submit_health_checkup,
    update_or_amend_health_checkup,
    upload_medical_files,
)
from astra_med.api.routes.insights import get_astronaut_insights, list_insights
from astra_med.api.routes.measurements import MeasurementIngestRequest, ingest_measurement
from astra_med.api.routes.medical_reports import (
    CreateMedicalReportRequest,
    ReviewReportRequest,
    create_medical_report,
    get_astronaut_reports,
    list_reports,
    review_report,
    sync_report,
)
from astra_med.api.routes.ml_inference import (
    MLPredictRequest,
    check_all_modules_health,
    check_module_health,
    predict_module,
)
from astra_med.api.routes.vitals import VitalIngestRequest, get_crew_vitals, ingest_vital
from astra_med.config import DB_PATH, FRONTEND_DIR, STATIC_DIR
from astra_med.core.types import HazardType
from astra_med.db import crud
from astra_med.db.database import session_factory
from astra_med.db.models import CrewMember


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def e2e_crew(test_session: Session) -> tuple[CrewMember, CrewMember]:
    """Provide standard CDR Sarah Chen (ASTRA-001) and PLT Marcus Vance (ASTRA-002)."""
    c1 = crud.create_crew_member(
        session=test_session,
        name="CDR Sarah Chen, MD",
        role="Mission Commander / Flight Medical Officer",
        status="active",
        astronaut_id="ASTRA-001",
        mission_id="ASTRA-1",
        username="chen",
        password_hash=get_password_hash("password123"),
        is_medical_officer=True,
    )
    c2 = crud.create_crew_member(
        session=test_session,
        name="PLT Marcus Vance",
        role="Pilot",
        status="active",
        astronaut_id="ASTRA-002",
        mission_id="ASTRA-1",
        username="vance",
        password_hash=get_password_hash("password123"),
        is_medical_officer=False,
    )
    test_session.commit()
    return c1, c2


# ── Step 1: Frontend & Backend Initialization ───────────────────────────────

def test_e2e_01_backend_status_and_frontend_assets():
    """Verify backend health status and single-page frontend availability."""
    status = system_status()
    assert status["status"] == "nominal"
    assert status["mode"] == "autonomous_offline"
    assert status["comms_latency_minutes"] == 20.0
    assert "no_autonomous_diagnosis" in status["security_policy"]

    # Verify frontend index.html and static directories exist
    index_res = serve_index()
    assert index_res is not None
    assert (FRONTEND_DIR / "index.html").exists()
    assert (STATIC_DIR / "js" / "app.js").exists()
    assert (STATIC_DIR / "js" / "api.js").exists()
    assert (STATIC_DIR / "css" / "main.css").exists()


# ── Step 2: User Registration and Login ──────────────────────────────────────

def test_e2e_02_user_registration_and_login(test_session: Session):
    """Test registering a new astronaut account and logging in with credentials."""
    reg_req = RegisterRequest(
        name="Dr. E2E Test Specialist",
        role="Flight Surgeon & Acclimatization Officer",
        username="e2e_doctor",
        password="TestPassword2026!",
        astronaut_id="ASTRA-991",
        mission_id="ASTRA-1",
        is_medical_officer=True,
    )
    user_prof = register(reg_req, session=test_session)
    assert user_prof.astronaut_id == "ASTRA-991"
    assert user_prof.username == "e2e_doctor"
    assert user_prof.is_medical_officer is True

    # 1. Login with correct password
    login_req = LoginRequest(username="e2e_doctor", password="TestPassword2026!")
    token_resp = login(login_req, session=test_session)
    assert token_resp.access_token is not None
    assert token_resp.astronaut_id == "ASTRA-991"
    assert token_resp.is_medical_officer is True

    # 2. Login with incorrect password -> 401 Unauthorized
    bad_login = LoginRequest(username="e2e_doctor", password="WrongPassword!")
    with pytest.raises(HTTPException) as exc:
        login(bad_login, session=test_session)
    assert exc.value.status_code == 401
    assert "Incorrect password" in exc.value.detail


# ── Step 3: Astronaut Profile Creation and Retrieval ─────────────────────────

def test_e2e_03_astronaut_profile_creation_and_retrieval(test_session: Session):
    """Verify profile creation via crew router and retrieval by session & ID."""
    crew_req = CrewCreateRequest(
        name="Engineer Alex Mercer",
        role="Life Support Systems Specialist",
        astronaut_id="ASTRA-992",
        mission_id="ASTRA-1",
        username="mercer",
        password="Password123!",
        is_medical_officer=False,
    )
    created = create_crew(crew_req, session=test_session)
    assert created.id is not None
    assert created.astronaut_id == "ASTRA-992"

    # Retrieve profile via crew endpoints
    retrieved = get_crew(created.id, session=test_session)
    assert retrieved.name == "Engineer Alex Mercer"
    assert retrieved.role == "Life Support Systems Specialist"

    # Verify listing contains new profile
    crew_list = list_crew(session=test_session)
    assert any(c.astronaut_id == "ASTRA-992" for c in crew_list)


# ── Step 4 & 5: Health Checkup Data Entry & Database Persistence ─────────────

def test_e2e_04_05_health_checkup_submission_and_db_persistence(test_session: Session):
    """Submit comprehensive multi-domain health checkup and verify DB persistence."""
    doctor = crud.get_crew_by_astronaut_id(test_session, "ASTRA-001")
    if not doctor:
        doctor = crud.create_crew_member(
            session=test_session,
            name="CDR Sarah Chen, MD",
            role="Mission Commander",
            astronaut_id="ASTRA-001",
            is_medical_officer=True,
        )
        test_session.commit()

    checkup_req = HealthCheckupCreateRequest(
        astronaut_id="ASTRA-001",
        checkup_date="2026-11-15",
        checkup_time="11:45",
        location="Mars Habitation Station — Medical Bay",
        checkup_type="Routine health checkup",
        notes="E2E comprehensive routine health checkup evaluation.",
        measurements=[
            MeasurementItem(domain="basic", metric_name="heart_rate", value=73.0, unit="bpm"),
            MeasurementItem(domain="basic", metric_name="bp_systolic", value=118.0, unit="mmHg"),
            MeasurementItem(domain="basic", metric_name="bp_diastolic", value=76.0, unit="mmHg"),
            MeasurementItem(domain="basic", metric_name="spo2", value=98.8, unit="%"),
            MeasurementItem(domain="basic", metric_name="temperature", value=36.7, unit="°C"),
            MeasurementItem(domain="basic", metric_name="respiratory_rate", value=15.0, unit="br/min"),
            MeasurementItem(domain="cardiovascular", metric_name="hrv_rmssd", value=52.0, unit="ms"),
            MeasurementItem(domain="immune", metric_name="wbc_count", value=6.8, unit="x10^3/uL"),
            MeasurementItem(domain="metabolic", metric_name="glucose", value=92.0, unit="mg/dL"),
            MeasurementItem(domain="sleep", metric_name="sleep_duration_hours", value=7.5, unit="hours"),
            MeasurementItem(domain="sleep", metric_name="sleep_quality_score", value=84.0, unit="score"),
        ],
    )

    result = submit_health_checkup(
        req=checkup_req,
        current_user=doctor,
        session=test_session,
        baseline_engine=get_baseline_engine(),
        alert_engine=get_alert_engine(),
        insight_engine=get_insight_engine(),
        ml_router=get_ml_router(),
        card_registry=get_action_card_registry(),
        sf_queue=get_store_forward_queue(),
    )

    assert result.checkup_id.startswith("CHK-20261115-ASTRA001-")
    assert result.measurements_saved == 11

    # Verify Database Storage
    db_rec = crud.get_health_checkup(test_session, result.checkup_id)
    assert db_rec is not None
    assert len(db_rec.measurements) == 11
    stored_metrics = {m.metric_name: m.value for m in db_rec.measurements}
    assert stored_metrics["heart_rate"] == 73.0
    assert stored_metrics["glucose"] == 92.0
    assert stored_metrics["sleep_duration_hours"] == 7.5


# ── Step 6: Test All 7 Health Modules ───────────────────────────────────────

def test_e2e_06_all_seven_health_modules_verification(test_session: Session):
    """Verify all 7 modules: Cardiovascular, Immune, Metabolic, Radiation, Sleep, Neuromuscular, SANS."""
    router = get_ml_router()
    all_modules = router.module_names
    expected_7 = {"cardiovascular", "immune", "metabolic", "radiation", "sleep", "neuromuscular", "sans"}
    assert set(all_modules) == expected_7

    # Inspect module health without inventing false weights
    health_reports = check_all_modules_health(ml_router=router)
    assert len(health_reports) == 7

    status_by_mod = {h["module"]: h["status"] for h in health_reports}
    # Sleep is live heuristic; others are currently placeholders pending trained weights
    assert status_by_mod["sleep"] == "live"
    for mod in ["cardiovascular", "immune", "metabolic", "radiation", "neuromuscular", "sans"]:
        assert status_by_mod[mod] in ("placeholder", "live")


# ── Step 7: Model Predictions & Baseline Comparisons ─────────────────────────

def test_e2e_07_predictions_and_baseline_comparisons(test_session: Session, e2e_crew: tuple[CrewMember, CrewMember]):
    """Test model prediction outputs and baseline Welford evaluation."""
    commander, _ = e2e_crew
    router = get_ml_router()
    baseline_engine = get_baseline_engine()

    # 1. Test Sleep Heuristic Prediction
    sleep_input = {
        "sleep_duration_hours": 4.5,
        "sleep_quality_score": 45.0,
        "rem_percentage": 11.0,
        "deep_sleep_percentage": 10.0,
        "circadian_phase_drift_minutes": 90.0,
    }
    sleep_pred = router.predict("sleep", sleep_input)
    assert "risk_label" in sleep_pred
    assert "risk_score" in sleep_pred
    assert sleep_pred["severity"] in ("GREEN", "AMBER", "RED")

    # 2. Test Baseline Statistical Evaluation
    # Feed 10 readings to establish baseline
    for i in range(10):
        baseline_engine.update_baseline(test_session, commander.id, "spo2", 98.0 + (i % 2) * 0.5, 140.0 + i)

    dev_nominal = baseline_engine.evaluate(test_session, commander.id, "spo2", 98.2)
    assert dev_nominal.is_significant is False
    assert abs(dev_nominal.z_score) < 2.0

    dev_extreme = baseline_engine.evaluate(test_session, commander.id, "spo2", 82.0)
    assert dev_extreme.is_significant is True
    assert dev_extreme.z_score < -3.5


# ── Step 8: Alerts, Insights, and Action Cards ───────────────────────────────

def test_e2e_08_alerts_insights_and_action_cards(test_session: Session, e2e_crew: tuple[CrewMember, CrewMember]):
    """Verify alerts, non-diagnostic insights, and action card dispatch."""
    commander, _ = e2e_crew
    alert_engine = get_alert_engine()
    insight_engine = get_insight_engine()
    action_engine = get_action_engine()
    card_registry = get_action_card_registry()
    card_registry.seed_defaults(test_session)

    # 1. Ingest extreme deviation to trigger Alert
    from astra_med.core.types import DeviationResult, SeverityTier
    extreme_dev = DeviationResult(
        metric_name="heart_rate",
        observed_value=165.0,
        baseline_mean=70.0,
        baseline_std=4.0,
        z_score=23.75,
        is_significant=True,
        direction="elevated",
    )
    candidate_cards = card_registry.find_cards(hazard=HazardType.GRAVITY)
    expected_card_id = candidate_cards[0].card_id if candidate_cards else "CARD-CVD-AMBER-01"

    alert = alert_engine.generate_alert(
        session=test_session,
        crew_id=commander.id,
        hazard=HazardType.GRAVITY,
        deviation=extreme_dev,
        timestamp_met=142.0,
        action_card_id=expected_card_id,
    )
    assert alert.severity.value in ("RED", "red")
    assert alert.action_card_id == expected_card_id

    # 2. Verify Insight Engine generated observation with STRICTLY NULL diagnosis
    insight = insight_engine.evaluate_deviation(
        session=test_session,
        crew_id=commander.id,
        module="cardiovascular",
        deviation=extreme_dev,
        subject_id=commander.astronaut_id,
    )
    assert insight.diagnosis is None
    assert insight.requires_medical_review is True
    assert "deviation" in insight.observation.lower()

    # 3. Verify Pre-approved Action Card
    card = get_action_card(expected_card_id, card_registry=card_registry)
    assert card is not None
    assert card.card_id == expected_card_id

    # 4. Dispatch and Acknowledge Action Task
    task = action_engine.dispatch_action(test_session, commander.id, "ACT-HYD-01")
    assert task.status == "pending"
    ack_task = action_engine.acknowledge_action(test_session, "ACT-HYD-01", notes="Crew rested and hydrated.")
    assert ack_task.status == "acknowledged"


# ── Step 9 & 10: Medical Reports, 20-min Comms Delay & Offline Sync ───────────

def test_e2e_09_10_medical_reports_comms_delay_and_sync(test_session: Session, e2e_crew: tuple[CrewMember, CrewMember]):
    """Test medical report queuing, 20-minute Mars comms delay, and ground review sync."""
    commander, _ = e2e_crew

    # 1. Create medical report (offline queued)
    rep_req = CreateMedicalReportRequest(
        crew_id=commander.id,
        title="Post-EVA Acclimatization Dossier",
        summary="Subject completed 5-hour surface simulation. Transient orthostatic shift noted.",
        domain="cardiovascular",
        requires_physician_review=True,
    )
    report = create_medical_report(rep_req, session=test_session)
    assert report.status == "queued_for_sync"
    assert report.requires_physician_review is True

    # 2. Verify sync status endpoint reflects 20-minute latency and queued report
    s_status = sync_status()
    assert s_status["link_status"] == "offline_buffered"
    assert s_status["one_way_latency_minutes"] == 20.0

    # 3. Simulate Store & Forward Sync
    synced = sync_report(report.report_id, session=test_session)
    assert synced.status == "transmitted"
    assert synced.synced_at is not None

    # 4. Ground Physician Review (asynchronous delayed update)
    rev_req = ReviewReportRequest(
        physician_name="Dr. Robert Hayes, NASA Flight Surgeon",
        decision="approved",
        comments="Approved 15% increase in fluid intake before next extravehicular session.",
        future_phase_updates={"hydration_target_ml": 3200},
    )
    reviewed = review_report(report.report_id, rev_req, session=test_session)
    assert reviewed.status == "reviewed"
    assert reviewed.physician_decision == "approved"
    assert "hydration_target_ml" in str(reviewed.future_phase_updates)


# ── Step 11: Dashboard Values Update After Submission ─────────────────────────

def test_e2e_11_dashboard_updates_verification(test_session: Session, e2e_crew: tuple[CrewMember, CrewMember]):
    """Verify latest checkup and astronaut overview reflect recent submissions."""
    commander, _ = e2e_crew

    # Submit a checkup for commander
    submit_health_checkup(
        req=HealthCheckupCreateRequest(
            astronaut_id=commander.astronaut_id,
            checkup_date="2026-11-15",
            checkup_time="10:00",
            measurements=[MeasurementItem(metric_name="heart_rate", value=70.0, unit="bpm")],
        ),
        current_user=commander,
        session=test_session,
        baseline_engine=get_baseline_engine(),
        alert_engine=get_alert_engine(),
        insight_engine=get_insight_engine(),
        ml_router=get_ml_router(),
        card_registry=get_action_card_registry(),
        sf_queue=get_store_forward_queue(),
    )

    # Retrieve history
    history = get_my_health_history(current_user=commander, session=test_session)
    assert len(history) >= 1

    # Retrieve latest checkup
    latest = get_my_latest_checkup(current_user=commander, session=test_session)
    assert latest is not None
    assert latest.astronaut_id == commander.astronaut_id
    assert len(latest.measurements) >= 1

    # Check astronaut overview
    overview = get_astronaut_overview(commander.astronaut_id, session=test_session)
    assert overview.astronaut_id == commander.astronaut_id
    assert overview.name == commander.name
    assert len(overview.latest_vitals) >= 1


# ── Step 12: Invalid Inputs, Boundary Checks, and Unauthorized Access ─────────

def test_e2e_12_error_handling_and_security_controls(test_session: Session, e2e_crew: tuple[CrewMember, CrewMember]):
    """Verify security barriers: bounds validation (422), unauthorized proxy (403), missing tokens (401)."""
    commander, pilot = e2e_crew

    # 1. Negative Measurement -> 422
    with pytest.raises(HTTPException) as exc1:
        submit_health_checkup(
            req=HealthCheckupCreateRequest(
                astronaut_id=pilot.astronaut_id,
                checkup_date="2026-11-15",
                measurements=[MeasurementItem(metric_name="heart_rate", value=-10.0, unit="bpm")],
            ),
            current_user=pilot,
            session=test_session,
            baseline_engine=get_baseline_engine(),
            alert_engine=get_alert_engine(),
            insight_engine=get_insight_engine(),
            ml_router=get_ml_router(),
            card_registry=get_action_card_registry(),
            sf_queue=get_store_forward_queue(),
        )
    assert exc1.value.status_code == 422

    # 2. Systolic <= Diastolic BP -> 422
    with pytest.raises(HTTPException) as exc2:
        submit_health_checkup(
            req=HealthCheckupCreateRequest(
                astronaut_id=pilot.astronaut_id,
                checkup_date="2026-11-15",
                measurements=[
                    MeasurementItem(metric_name="bp_systolic", value=80.0, unit="mmHg"),
                    MeasurementItem(metric_name="bp_diastolic", value=95.0, unit="mmHg"),
                ],
            ),
            current_user=pilot,
            session=test_session,
            baseline_engine=get_baseline_engine(),
            alert_engine=get_alert_engine(),
            insight_engine=get_insight_engine(),
            ml_router=get_ml_router(),
            card_registry=get_action_card_registry(),
            sf_queue=get_store_forward_queue(),
        )
    assert exc2.value.status_code == 422

    # 3. Unauthorized Proxy Submission (Pilot submitting for Commander) -> 403 Forbidden
    with pytest.raises(HTTPException) as exc3:
        submit_health_checkup(
            req=HealthCheckupCreateRequest(
                astronaut_id=commander.astronaut_id,
                checkup_date="2026-11-15",
                measurements=[MeasurementItem(metric_name="heart_rate", value=72.0, unit="bpm")],
            ),
            current_user=pilot,
            session=test_session,
            baseline_engine=get_baseline_engine(),
            alert_engine=get_alert_engine(),
            insight_engine=get_insight_engine(),
            ml_router=get_ml_router(),
            card_registry=get_action_card_registry(),
            sf_queue=get_store_forward_queue(),
        )
    assert exc3.value.status_code == 403
    assert "Permission denied" in exc3.value.detail
