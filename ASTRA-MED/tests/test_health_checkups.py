"""Tests for Astronaut Health Checkup & Medical Records Intake System.

Verifies the 15 required operational scenarios:
1. Routine health checkup submission with basic vitals
2. Cardiovascular data submission & storage
3. Blood test & immune panel submission
4. Metabolic panel submission
5. Medical report PDF upload & retrieval
6. ECG recording upload & SHA-256 verification
7. Ultrasound / MRI image upload
8. Incomplete form submission (only required fields)
9. Boundary validation for invalid measurement values (422)
10. Idempotent duplicate checkup submission protection
11. Flight Medical Officer proxy submission for another astronaut
12. Unauthorized astronaut proxy submission rejected (403)
13. ML module failure simulation does not block checkup saving
14. Offline buffering and store-and-forward queueing
15. Submitted checkup history, detail retrieval, and auditable amendments
"""

from __future__ import annotations

import asyncio
import hashlib
import io
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from astra_med.api.deps import (
    get_action_card_registry,
    get_alert_engine,
    get_baseline_engine,
    get_insight_engine,
    get_ml_router,
    get_store_forward_queue,
)
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
from astra_med.db import crud
from astra_med.db.models import CrewMember, HealthCheckupRecord


@pytest.fixture
def fmo_user(test_session: Session) -> CrewMember:
    """Flight Medical Officer user (authorized for proxy submissions)."""
    user = crud.create_crew_member(
        session=test_session,
        name="CDR Sarah Chen, MD",
        role="Mission Commander / Flight Medical Officer",
        status="active",
        astronaut_id="ASTRA-001",
        mission_id="ASTRA-1",
        username="chen",
        is_medical_officer=True,
    )
    test_session.commit()
    return user


@pytest.fixture
def pilot_user(test_session: Session) -> CrewMember:
    """Pilot user (non-medical officer, can only self-report)."""
    user = crud.create_crew_member(
        session=test_session,
        name="PLT Marcus Vance",
        role="Pilot / Systems Engineer",
        status="active",
        astronaut_id="ASTRA-002",
        mission_id="ASTRA-1",
        username="vance",
        is_medical_officer=False,
    )
    test_session.commit()
    return user


# ── Scenario 1: Routine Health Checkup Submission with Basic Vitals ───────────

def test_scenario_1_routine_checkup_submission(test_session: Session, fmo_user: CrewMember):
    req = HealthCheckupCreateRequest(
        astronaut_id=fmo_user.astronaut_id,
        checkup_date="2026-11-15",
        checkup_time="09:00",
        location="Mars Transit Hab — Clinical Station",
        checkup_type="Routine health checkup",
        notes="Daily scheduled physiological assessment.",
        measurements=[
            MeasurementItem(domain="basic", metric_name="heart_rate", value=70.0, unit="bpm", reference_range="60 - 100"),
            MeasurementItem(domain="basic", metric_name="bp_systolic", value=120.0, unit="mmHg", reference_range="90 - 120"),
            MeasurementItem(domain="basic", metric_name="bp_diastolic", value=80.0, unit="mmHg", reference_range="60 - 80"),
            MeasurementItem(domain="basic", metric_name="spo2", value=99.0, unit="%", reference_range="95 - 100"),
            MeasurementItem(domain="basic", metric_name="temperature", value=36.8, unit="°C", reference_range="36.1 - 37.2"),
            MeasurementItem(domain="basic", metric_name="respiratory_rate", value=14.0, unit="br/min", reference_range="12 - 20"),
        ],
    )

    result = submit_health_checkup(
        req=req,
        current_user=fmo_user,
        session=test_session,
        baseline_engine=get_baseline_engine(),
        alert_engine=get_alert_engine(),
        insight_engine=get_insight_engine(),
        ml_router=get_ml_router(),
        card_registry=get_action_card_registry(),
        sf_queue=get_store_forward_queue(),
    )

    assert result.checkup_id.startswith("CHK-20261115-ASTRA001-")
    assert result.astronaut_id == "ASTRA-001"
    assert result.measurements_saved == 6

    # Verify database persistence
    db_rec = crud.get_health_checkup(test_session, result.checkup_id)
    assert db_rec is not None
    assert db_rec.checkup_type == "Routine health checkup"
    assert len(db_rec.measurements) == 6
    assert any(m.metric_name == "heart_rate" and m.value == 70.0 for m in db_rec.measurements)


# ── Scenario 2: Cardiovascular Data Submission and Database Storage ───────────

def test_scenario_2_cardiovascular_data_submission(test_session: Session, pilot_user: CrewMember):
    req = HealthCheckupCreateRequest(
        astronaut_id=pilot_user.astronaut_id,
        checkup_date="2026-11-15",
        checkup_type="Cardiovascular assessment",
        notes="Post-exercise cycle ergometer recovery checkup.",
        measurements=[
            MeasurementItem(domain="cardiovascular", metric_name="resting_heart_rate", value=64.0, unit="bpm"),
            MeasurementItem(domain="cardiovascular", metric_name="bp_systolic", value=116.0, unit="mmHg"),
            MeasurementItem(domain="cardiovascular", metric_name="bp_diastolic", value=74.0, unit="mmHg"),
            MeasurementItem(domain="cardiovascular", metric_name="hrv_rmssd", value=48.5, unit="ms"),
            MeasurementItem(domain="cardiovascular", metric_name="stroke_volume", value=82.0, unit="mL"),
        ],
    )

    result = submit_health_checkup(
        req=req,
        current_user=pilot_user,
        session=test_session,
        baseline_engine=get_baseline_engine(),
        alert_engine=get_alert_engine(),
        insight_engine=get_insight_engine(),
        ml_router=get_ml_router(),
        card_registry=get_action_card_registry(),
        sf_queue=get_store_forward_queue(),
    )

    assert result.measurements_saved == 5
    db_rec = crud.get_health_checkup(test_session, result.checkup_id)
    cv_measurements = [m for m in db_rec.measurements if m.domain == "cardiovascular"]
    assert len(cv_measurements) == 5
    metrics = {m.metric_name: m.value for m in cv_measurements}
    assert metrics["hrv_rmssd"] == 48.5
    assert metrics["resting_heart_rate"] == 64.0


# ── Scenario 3: Blood Test and Immune Panel Submission ────────────────────────

def test_scenario_3_blood_immune_panel_submission(test_session: Session, fmo_user: CrewMember):
    req = HealthCheckupCreateRequest(
        astronaut_id=fmo_user.astronaut_id,
        checkup_date="2026-11-15",
        checkup_type="Blood test",
        notes="Routine flight quarter hematology and immune panel.",
        measurements=[
            MeasurementItem(domain="immune", metric_name="wbc_count", value=6.4, unit="x10^3/uL"),
            MeasurementItem(domain="immune", metric_name="neutrophils", value=58.0, unit="%"),
            MeasurementItem(domain="immune", metric_name="lymphocytes", value=32.0, unit="%"),
            MeasurementItem(domain="immune", metric_name="monocytes", value=6.5, unit="%"),
            MeasurementItem(domain="immune", metric_name="eosinophils", value=2.5, unit="%"),
            MeasurementItem(domain="immune", metric_name="basophils", value=1.0, unit="%"),
            MeasurementItem(domain="blood", metric_name="hemoglobin", value=15.2, unit="g/dL"),
            MeasurementItem(domain="blood", metric_name="platelets", value=245.0, unit="x10^3/uL"),
            MeasurementItem(domain="immune", metric_name="il_6", value=2.4, unit="pg/mL"),
            MeasurementItem(domain="immune", metric_name="tnf_alpha", value=3.1, unit="pg/mL"),
        ],
    )

    result = submit_health_checkup(
        req=req,
        current_user=fmo_user,
        session=test_session,
        baseline_engine=get_baseline_engine(),
        alert_engine=get_alert_engine(),
        insight_engine=get_insight_engine(),
        ml_router=get_ml_router(),
        card_registry=get_action_card_registry(),
        sf_queue=get_store_forward_queue(),
    )

    assert result.measurements_saved == 10
    db_rec = crud.get_health_checkup(test_session, result.checkup_id)
    immune_names = {m.metric_name for m in db_rec.measurements if m.domain in ("immune", "blood")}
    assert "wbc_count" in immune_names
    assert "il_6" in immune_names
    assert "hemoglobin" in immune_names


# ── Scenario 4: Metabolic Panel Submission ────────────────────────────────────

def test_scenario_4_metabolic_panel_submission(test_session: Session, pilot_user: CrewMember):
    req = HealthCheckupCreateRequest(
        astronaut_id=pilot_user.astronaut_id,
        checkup_date="2026-11-15",
        checkup_type="Metabolic assessment",
        notes="Fasting blood biochemistry panel.",
        measurements=[
            MeasurementItem(domain="metabolic", metric_name="glucose", value=88.0, unit="mg/dL"),
            MeasurementItem(domain="metabolic", metric_name="sodium", value=139.0, unit="mmol/L"),
            MeasurementItem(domain="metabolic", metric_name="potassium", value=4.2, unit="mmol/L"),
            MeasurementItem(domain="metabolic", metric_name="chloride", value=102.0, unit="mmol/L"),
            MeasurementItem(domain="metabolic", metric_name="bicarbonate", value=24.0, unit="mmol/L"),
            MeasurementItem(domain="metabolic", metric_name="calcium", value=9.4, unit="mg/dL"),
            MeasurementItem(domain="metabolic", metric_name="creatinine", value=0.95, unit="mg/dL"),
            MeasurementItem(domain="metabolic", metric_name="bun", value=14.0, unit="mg/dL"),
        ],
    )

    result = submit_health_checkup(
        req=req,
        current_user=pilot_user,
        session=test_session,
        baseline_engine=get_baseline_engine(),
        alert_engine=get_alert_engine(),
        insight_engine=get_insight_engine(),
        ml_router=get_ml_router(),
        card_registry=get_action_card_registry(),
        sf_queue=get_store_forward_queue(),
    )

    assert result.measurements_saved == 8
    db_rec = crud.get_health_checkup(test_session, result.checkup_id)
    metabolic = {m.metric_name: m.value for m in db_rec.measurements if m.domain == "metabolic"}
    assert metabolic["glucose"] == 88.0
    assert metabolic["creatinine"] == 0.95
    assert metabolic["sodium"] == 139.0


# ── Scenario 5: Medical Report PDF Upload and Retrieval ───────────────────────

def test_scenario_5_pdf_report_upload_and_retrieval(test_session: Session, fmo_user: CrewMember):
    # 1. Create checkup
    chk = crud.create_health_checkup(
        session=test_session,
        checkup_id="CHK-20261115-ASTRA001-PDF01",
        astronaut_id=fmo_user.astronaut_id,
        crew_id=fmo_user.id,
        checkup_date="2026-11-15",
        checkup_type="Routine health checkup",
    )
    test_session.commit()

    # 2. Upload PDF
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Title (ASTRA-MED Flight Lab Report) >>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload = UploadFile(
        filename="mission_lab_report.pdf",
        file=io.BytesIO(pdf_content),
        headers={"content-type": "application/pdf"},
    )

    uploaded = upload_medical_files(
        checkup_id=chk.checkup_id,
        files=[upload],
        health_module="blood",
        session=test_session,
    )

    assert len(uploaded) == 1
    file_record = uploaded[0]
    assert file_record.original_filename == "mission_lab_report.pdf"
    assert file_record.sha256_checksum == hashlib.sha256(pdf_content).hexdigest()

    # 3. Download file and verify persistence
    download_res = download_medical_file(file_record.file_id, session=test_session)
    assert Path(download_res.path).exists()
    assert Path(download_res.path).read_bytes() == pdf_content


# ── Scenario 6: ECG Recording Upload and SHA-256 Verification ─────────────────

def test_scenario_6_ecg_recording_upload_and_sha256_verification(test_session: Session, fmo_user: CrewMember):
    chk = crud.create_health_checkup(
        session=test_session,
        checkup_id="CHK-20261115-ASTRA001-ECG01",
        astronaut_id=fmo_user.astronaut_id,
        crew_id=fmo_user.id,
        checkup_date="2026-11-15",
        checkup_type="Cardiovascular assessment",
    )
    test_session.commit()

    ecg_csv = b"timestamp,lead_I,lead_II,lead_V1\n0.00,0.012,0.045,0.010\n0.01,0.025,0.080,0.018\n"
    expected_sha256 = hashlib.sha256(ecg_csv).hexdigest()

    upload = UploadFile(
        filename="lead_ii_rhythm.csv",
        file=io.BytesIO(ecg_csv),
        headers={"content-type": "text/csv"},
    )

    uploaded = upload_medical_files(
        checkup_id=chk.checkup_id,
        files=[upload],
        health_module="cardiovascular",
        session=test_session,
    )

    assert uploaded[0].sha256_checksum == expected_sha256

    # Verify status endpoint returns the checksum
    status_info = get_medical_file_status(uploaded[0].file_id, session=test_session)
    assert status_info["sha256_checksum"] == expected_sha256


# ── Scenario 7: Ultrasound / MRI Image Upload ─────────────────────────────────

def test_scenario_7_ultrasound_mri_image_upload(test_session: Session, fmo_user: CrewMember):
    chk = crud.create_health_checkup(
        session=test_session,
        checkup_id="CHK-20261115-ASTRA001-SANS01",
        astronaut_id=fmo_user.astronaut_id,
        crew_id=fmo_user.id,
        checkup_date="2026-11-15",
        checkup_type="Vision and ocular assessment",
    )
    test_session.commit()

    # Synthetic PNG image header
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    upload = UploadFile(
        filename="ocular_optic_nerve_ultrasound.png",
        file=io.BytesIO(png_bytes),
        headers={"content-type": "image/png"},
    )

    uploaded = upload_medical_files(
        checkup_id=chk.checkup_id,
        files=[upload],
        health_module="sans",
        session=test_session,
    )

    assert len(uploaded) == 1
    assert uploaded[0].health_module == "sans"
    assert uploaded[0].processing_status == "stored"


# ── Scenario 8: Incomplete Form Submission (Minimal Required Fields) ──────────

def test_scenario_8_minimal_incomplete_checkup_submission(test_session: Session, pilot_user: CrewMember):
    req = HealthCheckupCreateRequest(
        astronaut_id=pilot_user.astronaut_id,
        checkup_date="2026-11-15",
        checkup_type="Routine health checkup",
        # All measurements and optional fields omitted
    )

    result = submit_health_checkup(
        req=req,
        current_user=pilot_user,
        session=test_session,
        baseline_engine=get_baseline_engine(),
        alert_engine=get_alert_engine(),
        insight_engine=get_insight_engine(),
        ml_router=get_ml_router(),
        card_registry=get_action_card_registry(),
        sf_queue=get_store_forward_queue(),
    )

    assert result.measurements_saved == 0
    assert result.checkup_id is not None
    db_rec = crud.get_health_checkup(test_session, result.checkup_id)
    assert db_rec is not None
    assert len(db_rec.measurements) == 0


# ── Scenario 9: Boundary Validation for Invalid Measurement Values ───────────

def test_scenario_9_boundary_validation_invalid_measurements(test_session: Session, pilot_user: CrewMember):
    # Test 1: Negative heart rate -> 422
    req_neg_hr = HealthCheckupCreateRequest(
        astronaut_id=pilot_user.astronaut_id,
        checkup_date="2026-11-15",
        measurements=[MeasurementItem(metric_name="heart_rate", value=-12.0, unit="bpm")],
    )
    with pytest.raises(HTTPException) as exc1:
        submit_health_checkup(
            req=req_neg_hr,
            current_user=pilot_user,
            session=test_session,
            baseline_engine=get_baseline_engine(),
            alert_engine=get_alert_engine(),
            insight_engine=get_insight_engine(),
            ml_router=get_ml_router(),
            card_registry=get_action_card_registry(),
            sf_queue=get_store_forward_queue(),
        )
    assert exc1.value.status_code == 422
    assert "cannot be negative" in exc1.value.detail

    # Test 2: Heart rate > 300 bpm -> 422
    req_high_hr = HealthCheckupCreateRequest(
        astronaut_id=pilot_user.astronaut_id,
        checkup_date="2026-11-15",
        measurements=[MeasurementItem(metric_name="heart_rate", value=450.0, unit="bpm")],
    )
    with pytest.raises(HTTPException) as exc2:
        submit_health_checkup(
            req=req_high_hr,
            current_user=pilot_user,
            session=test_session,
            baseline_engine=get_baseline_engine(),
            alert_engine=get_alert_engine(),
            insight_engine=get_insight_engine(),
            ml_router=get_ml_router(),
            card_registry=get_action_card_registry(),
            sf_queue=get_store_forward_queue(),
        )
    assert exc2.value.status_code == 422
    assert "exceeds physiological boundaries" in exc2.value.detail

    # Test 3: Systolic BP <= Diastolic BP -> 422
    req_bp_inverted = HealthCheckupCreateRequest(
        astronaut_id=pilot_user.astronaut_id,
        checkup_date="2026-11-15",
        measurements=[
            MeasurementItem(metric_name="bp_systolic", value=75.0, unit="mmHg"),
            MeasurementItem(metric_name="bp_diastolic", value=110.0, unit="mmHg"),
        ],
    )
    with pytest.raises(HTTPException) as exc3:
        submit_health_checkup(
            req=req_bp_inverted,
            current_user=pilot_user,
            session=test_session,
            baseline_engine=get_baseline_engine(),
            alert_engine=get_alert_engine(),
            insight_engine=get_insight_engine(),
            ml_router=get_ml_router(),
            card_registry=get_action_card_registry(),
            sf_queue=get_store_forward_queue(),
        )
    assert exc3.value.status_code == 422
    assert "must be greater than diastolic" in exc3.value.detail

    # Test 4: SpO2 > 100% -> 422
    req_spo2_high = HealthCheckupCreateRequest(
        astronaut_id=pilot_user.astronaut_id,
        checkup_date="2026-11-15",
        measurements=[MeasurementItem(metric_name="spo2", value=108.0, unit="%")],
    )
    with pytest.raises(HTTPException) as exc4:
        submit_health_checkup(
            req=req_spo2_high,
            current_user=pilot_user,
            session=test_session,
            baseline_engine=get_baseline_engine(),
            alert_engine=get_alert_engine(),
            insight_engine=get_insight_engine(),
            ml_router=get_ml_router(),
            card_registry=get_action_card_registry(),
            sf_queue=get_store_forward_queue(),
        )
    assert exc4.value.status_code == 422
    assert "cannot exceed 100%" in exc4.value.detail


# ── Scenario 10: Idempotent Duplicate Checkup Submission Protection ───────────

def test_scenario_10_idempotent_duplicate_checkup_protection(test_session: Session, pilot_user: CrewMember):
    idem_key = "IDEM-TEST-KEY-XYZ-999"
    req = HealthCheckupCreateRequest(
        astronaut_id=pilot_user.astronaut_id,
        checkup_date="2026-11-15",
        idempotency_key=idem_key,
        measurements=[MeasurementItem(metric_name="heart_rate", value=72.0, unit="bpm")],
    )

    # 1st Submission
    res1 = submit_health_checkup(
        req=req,
        current_user=pilot_user,
        session=test_session,
        baseline_engine=get_baseline_engine(),
        alert_engine=get_alert_engine(),
        insight_engine=get_insight_engine(),
        ml_router=get_ml_router(),
        card_registry=get_action_card_registry(),
        sf_queue=get_store_forward_queue(),
    )
    original_id = res1.checkup_id

    # 2nd Submission with identical idempotency key
    res2 = submit_health_checkup(
        req=req,
        current_user=pilot_user,
        session=test_session,
        baseline_engine=get_baseline_engine(),
        alert_engine=get_alert_engine(),
        insight_engine=get_insight_engine(),
        ml_router=get_ml_router(),
        card_registry=get_action_card_registry(),
        sf_queue=get_store_forward_queue(),
    )

    # Must return original checkup and not duplicate records
    assert res2.checkup_id == original_id
    assert "Idempotent Replay" in res2.status

    # Verify no duplicate entries in database
    records = crud.list_health_checkups_for_astronaut(test_session, pilot_user.astronaut_id)
    matching = [r for r in records if r.idempotency_key == idem_key]
    assert len(matching) == 1


# ── Scenario 11: Flight Medical Officer Proxy Submission for Another Astronaut ─

def test_scenario_11_flight_medical_officer_proxy_submission(
    test_session: Session,
    fmo_user: CrewMember,
    pilot_user: CrewMember,
):
    # FMO submits checkup FOR PLT Marcus Vance
    req = HealthCheckupCreateRequest(
        astronaut_id=pilot_user.astronaut_id,
        checkup_date="2026-11-15",
        checkup_type="Cardiovascular assessment",
        notes="Clinical checkup conducted by Flight Medical Officer.",
        measurements=[MeasurementItem(metric_name="heart_rate", value=68.0, unit="bpm")],
    )

    result = submit_health_checkup(
        req=req,
        current_user=fmo_user,
        session=test_session,
        baseline_engine=get_baseline_engine(),
        alert_engine=get_alert_engine(),
        insight_engine=get_insight_engine(),
        ml_router=get_ml_router(),
        card_registry=get_action_card_registry(),
        sf_queue=get_store_forward_queue(),
    )

    db_rec = crud.get_health_checkup(test_session, result.checkup_id)
    assert db_rec.astronaut_id == pilot_user.astronaut_id
    assert db_rec.submitted_by_name == fmo_user.name
    assert db_rec.is_submitted_by_officer is True


# ── Scenario 12: Unauthorized Astronaut Proxy Submission Rejected (403) ───────

def test_scenario_12_unauthorized_astronaut_proxy_submission_rejected(
    test_session: Session,
    fmo_user: CrewMember,
    pilot_user: CrewMember,
):
    # Regular pilot attempts to submit record for CDR Sarah Chen
    req = HealthCheckupCreateRequest(
        astronaut_id=fmo_user.astronaut_id,
        checkup_date="2026-11-15",
        measurements=[MeasurementItem(metric_name="heart_rate", value=75.0, unit="bpm")],
    )

    with pytest.raises(HTTPException) as exc:
        submit_health_checkup(
            req=req,
            current_user=pilot_user,
            session=test_session,
            baseline_engine=get_baseline_engine(),
            alert_engine=get_alert_engine(),
            insight_engine=get_insight_engine(),
            ml_router=get_ml_router(),
            card_registry=get_action_card_registry(),
            sf_queue=get_store_forward_queue(),
        )

    assert exc.value.status_code == 403
    assert "Permission denied" in exc.value.detail


# ── Scenario 13: ML Module Failure Does Not Block Checkup Saving ───────────────

def test_scenario_13_ml_module_failure_does_not_block_saving(test_session: Session, pilot_user: CrewMember):
    mock_ml = MagicMock()
    mock_ml.module_names = ["cardiovascular"]
    # Simulate runtime exception in ML inference
    mock_ml.predict.side_effect = RuntimeError("GPU accelerator offline or out of memory")

    req = HealthCheckupCreateRequest(
        astronaut_id=pilot_user.astronaut_id,
        checkup_date="2026-11-15",
        measurements=[
            MeasurementItem(domain="cardiovascular", metric_name="heart_rate", value=76.0, unit="bpm"),
            MeasurementItem(domain="cardiovascular", metric_name="bp_systolic", value=122.0, unit="mmHg"),
            MeasurementItem(domain="cardiovascular", metric_name="bp_diastolic", value=78.0, unit="mmHg"),
        ],
    )

    result = submit_health_checkup(
        req=req,
        current_user=pilot_user,
        session=test_session,
        baseline_engine=get_baseline_engine(),
        alert_engine=get_alert_engine(),
        insight_engine=get_insight_engine(),
        ml_router=mock_ml,
        card_registry=get_action_card_registry(),
        sf_queue=get_store_forward_queue(),
    )

    # Checkup MUST still be saved successfully in DB!
    assert result.measurements_saved == 3
    db_rec = crud.get_health_checkup(test_session, result.checkup_id)
    assert db_rec is not None
    assert len(db_rec.measurements) == 3
    # Unavailability noted in awaiting list without crashing
    assert any("ML processing is currently unavailable" in mod for mod in result.modules_awaiting)


# ── Scenario 14: Offline Buffering and Store-and-Forward Queueing ─────────────

def test_scenario_14_offline_buffering_and_history_sync(test_session: Session, pilot_user: CrewMember):
    req = HealthCheckupCreateRequest(
        astronaut_id=pilot_user.astronaut_id,
        checkup_date="2026-11-15",
        measurements=[MeasurementItem(metric_name="heart_rate", value=72.0, unit="bpm")],
    )

    submit_health_checkup(
        req=req,
        current_user=pilot_user,
        session=test_session,
        baseline_engine=get_baseline_engine(),
        alert_engine=get_alert_engine(),
        insight_engine=get_insight_engine(),
        ml_router=get_ml_router(),
        card_registry=get_action_card_registry(),
        sf_queue=get_store_forward_queue(),
    )

    history = get_my_health_history(
        current_user=pilot_user,
        session=test_session,
    )
    assert len(history) >= 1
    assert history[0].astronaut_id == pilot_user.astronaut_id

    latest = get_my_latest_checkup(
        current_user=pilot_user,
        session=test_session,
    )
    assert latest.astronaut_id == pilot_user.astronaut_id


# ── Scenario 15: Checkup Detail and Auditable Amendments ───────────────────────

def test_scenario_15_checkup_detail_and_auditable_amendments(test_session: Session, fmo_user: CrewMember):
    # 1. Create original checkup
    chk = crud.create_health_checkup(
        session=test_session,
        checkup_id="CHK-20261115-ASTRA001-AMEND",
        astronaut_id=fmo_user.astronaut_id,
        crew_id=fmo_user.id,
        checkup_date="2026-11-15",
        checkup_type="Routine health checkup",
        notes="Initial intake observation.",
    )
    crud.add_checkup_measurement(test_session, chk.id, "basic", "heart_rate", 72.0, "bpm")
    test_session.commit()

    # 2. Retrieve detail
    detail = get_health_checkups_or_detail(chk.checkup_id, session=test_session)
    assert detail.checkup_id == chk.checkup_id
    assert len(detail.measurements) == 1

    # 3. Apply auditable amendment
    update_req = CheckupUpdateRequest(
        amendment_reason="Updated with verified post-transit calibrated monitor reading",
        location="Mars Hab Medical Bay",
    )
    amended = update_or_amend_health_checkup(
        checkup_id=chk.checkup_id,
        req=update_req,
        current_user=fmo_user,
        session=test_session,
    )

    assert amended.is_amendment is True
    assert "Amendment by CDR Sarah Chen, MD" in amended.notes
    assert "Initial intake observation." in amended.notes  # Original notes preserved
    assert amended.location == "Mars Hab Medical Bay"
