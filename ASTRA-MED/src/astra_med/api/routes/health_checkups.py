"""API Routes for Astronaut Health Checkup & Medical Records Intake System.

Handles:
- Checkup creation and auditable amendments
- Multi-domain physiological measurement submission
- Secure medical report and instrument artifact uploads
- Routing to ML analytical modules and the Insight Engine
- Role-based authorization (astronaut self-reporting vs. flight surgeon proxy submission)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from astra_med.api.auth import get_current_user
from astra_med.api.deps import (
    get_action_card_registry,
    get_action_engine,
    get_alert_engine,
    get_baseline_engine,
    get_db,
    get_insight_engine,
    get_ml_router,
    get_store_forward_queue,
)
from astra_med.config import (
    ALLOWED_FILE_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    MEDICAL_FILES_DIR,
)
from astra_med.core.action_cards import ActionCardRegistry
from astra_med.core.action_engine import ActionEngine
from astra_med.core.alert_engine import AlertEngine
from astra_med.core.baseline import PersonalBaselineEngine
from astra_med.core.insight_engine import InsightEngine
from astra_med.core.store_forward import StoreAndForwardQueue
from astra_med.core.types import HazardType
from astra_med.db import crud
from astra_med.db.models import CrewMember
from astra_med.ml.router import MLRouter

router = APIRouter(tags=["Health Checkup & Medical Records"])


# ── Request / Response Schemas ───────────────────────────────────────────

class MeasurementItem(BaseModel):
    domain: str = "general"
    metric_name: str
    value: float
    unit: str
    reference_range: Optional[str] = None
    data_source: str = "manual_entry"


class HealthCheckupCreateRequest(BaseModel):
    astronaut_id: str
    checkup_date: str  # YYYY-MM-DD
    checkup_time: Optional[str] = None  # HH:MM
    location: Optional[str] = "Mars Transit Hab — Clinical Station"
    medical_officer: Optional[str] = None
    checkup_type: str = "Routine health checkup"
    notes: Optional[str] = None
    idempotency_key: Optional[str] = None
    measurements: List[MeasurementItem] = Field(default_factory=list)


class CheckupUpdateRequest(BaseModel):
    notes: Optional[str] = None
    medical_officer: Optional[str] = None
    location: Optional[str] = None
    submission_status: Optional[str] = None
    amendment_reason: Optional[str] = None


class MeasurementResponseModel(BaseModel):
    id: int
    domain: str
    metric_name: str
    value: float
    unit: str
    reference_range: Optional[str] = None
    data_source: str

    model_config = ConfigDict(from_attributes=True)


class MedicalFileResponseModel(BaseModel):
    id: int
    file_id: str
    original_filename: str
    health_module: str
    file_size_bytes: int
    mime_type: str
    sha256_checksum: str
    processing_status: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class HealthCheckupDetailResponse(BaseModel):
    id: int
    checkup_id: str
    astronaut_id: str
    crew_name: str
    crew_role: str
    checkup_date: str
    checkup_time: Optional[str] = None
    location: Optional[str] = None
    medical_officer: Optional[str] = None
    checkup_type: str
    notes: Optional[str] = None
    submission_status: str
    submitted_by_name: Optional[str] = None
    is_submitted_by_officer: bool
    is_amendment: bool
    amends_checkup_id: Optional[str] = None
    created_at: str
    measurements: List[MeasurementResponseModel] = []
    files: List[MedicalFileResponseModel] = []

    model_config = ConfigDict(from_attributes=True)


class HealthCheckupSubmissionConfirmation(BaseModel):
    status: str = "Health Checkup Submitted Successfully"
    checkup_id: str
    astronaut_id: str
    checkup_date: str
    measurements_saved: int
    files_uploaded: int
    modules_processed: List[str]
    modules_awaiting: List[str]
    validation_warnings: List[str]
    record_url: str


# ── Health Checkup Endpoints ─────────────────────────────────────────────

@router.post("/health-checkups", response_model=HealthCheckupSubmissionConfirmation, status_code=status.HTTP_201_CREATED)
def submit_health_checkup(
    req: HealthCheckupCreateRequest,
    current_user: CrewMember = Depends(get_current_user),
    session: Session = Depends(get_db),
    baseline_engine: PersonalBaselineEngine = Depends(get_baseline_engine),
    alert_engine: AlertEngine = Depends(get_alert_engine),
    insight_engine: InsightEngine = Depends(get_insight_engine),
    ml_router: MLRouter = Depends(get_ml_router),
    card_registry: ActionCardRegistry = Depends(get_action_card_registry),
    sf_queue: StoreAndForwardQueue = Depends(get_store_forward_queue),
):
    """Submit a complete health checkup record with discrete measurements and route to ML/Insight engines."""
    # 1. Target Astronaut Identification
    target_crew = crud.get_crew_by_astronaut_id(session, req.astronaut_id)
    if not target_crew:
        # Auto-create if initial demo ID
        target_crew = crud.create_crew_member(
            session=session,
            name=f"Astronaut {req.astronaut_id}",
            role="Mission Specialist",
            astronaut_id=req.astronaut_id,
        )

    # 2. Role-Based Access Control
    # Astronauts can only submit for themselves unless they are medical officers
    is_medical_officer = (
        current_user.is_medical_officer
        or any(k in current_user.role.lower() for k in ["medical", "doctor", "surgeon", "physician"])
    )
    is_self_submission = (current_user.astronaut_id == target_crew.astronaut_id or current_user.id == target_crew.id)

    if not is_self_submission and not is_medical_officer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: You cannot submit health checkup data on behalf of astronaut {req.astronaut_id} without authorized medical personnel privileges.",
        )

    # 3. Validate Measurement Boundaries & Biological Constraints
    systolic_val = None
    diastolic_val = None

    for m in req.measurements:
        # Negative value checks
        if m.value < 0:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid measurement: {m.metric_name} value ({m.value}) cannot be negative.",
            )
        # Heart rate boundaries (human limits: > 300 bpm impossible)
        if m.metric_name in ("heart_rate", "resting_heart_rate"):
            if m.value < 20 or m.value > 300:
                raise HTTPException(
                    status_code=422,
                    detail=f"Heart rate {m.value} bpm exceeds physiological boundaries (20 - 300 bpm).",
                )
        # Blood pressure checks
        if m.metric_name in ("bp_systolic", "systolic"):
            systolic_val = m.value
        if m.metric_name in ("bp_diastolic", "diastolic"):
            diastolic_val = m.value
        # SpO2 boundaries
        if m.metric_name == "spo2":
            if m.value > 100:
                raise HTTPException(
                    status_code=422,
                    detail=f"SpO2 oxygen saturation ({m.value}%) cannot exceed 100%.",
                )
        # Respiratory rate
        if m.metric_name == "respiratory_rate":
            if m.value > 80:
                raise HTTPException(
                    status_code=422,
                    detail=f"Respiratory rate ({m.value}) exceeds physiological limit (80 bpm).",
                )

    if systolic_val is not None and diastolic_val is not None:
        if systolic_val <= diastolic_val:
            raise HTTPException(
                status_code=422,
                detail=f"Systolic blood pressure ({systolic_val} mmHg) must be greater than diastolic blood pressure ({diastolic_val} mmHg).",
            )

    # 4. Check for Idempotency
    if req.idempotency_key:
        existing = crud.get_health_checkup_by_idempotency_key(session, req.idempotency_key) if hasattr(crud, "get_health_checkup_by_idempotency_key") else None
        if not existing:
            from sqlalchemy import select
            from astra_med.db.models import HealthCheckupRecord
            existing = session.execute(
                select(HealthCheckupRecord).where(HealthCheckupRecord.idempotency_key == req.idempotency_key)
            ).scalar_one_or_none()

        if existing:
            return HealthCheckupSubmissionConfirmation(
                status="Health Checkup Submitted Successfully (Idempotent Replay)",
                checkup_id=existing.checkup_id,
                astronaut_id=existing.astronaut_id,
                checkup_date=existing.checkup_date,
                measurements_saved=len(existing.measurements),
                files_uploaded=len(existing.files) if existing.files else 0,
                modules_processed=["previously_processed"],
                modules_awaiting=[],
                validation_warnings=[],
                record_url=f"#/health-records?id={existing.checkup_id}",
            )

    # 5. Create Checkup Header
    date_code = req.checkup_date.replace("-", "")
    unique_suffix = uuid.uuid4().hex[:6].upper()
    checkup_id = f"CHK-{date_code}-{req.astronaut_id.replace('-', '')}-{unique_suffix}"

    checkup = crud.create_health_checkup(
        session=session,
        checkup_id=checkup_id,
        astronaut_id=target_crew.astronaut_id,
        crew_id=target_crew.id,
        checkup_date=req.checkup_date,
        checkup_type=req.checkup_type,
        checkup_time=req.checkup_time,
        location=req.location,
        medical_officer=req.medical_officer or (current_user.name if is_medical_officer and not is_self_submission else None),
        notes=req.notes,
        submitted_by_crew_id=current_user.id,
        submitted_by_name=current_user.name,
        is_submitted_by_officer=is_medical_officer and not is_self_submission,
        idempotency_key=req.idempotency_key,
    )

    # 6. Save Measurements & Route to ML Modules
    measurements_saved = 0
    validation_warnings: List[str] = []
    modules_processed: List[str] = []
    modules_awaiting: List[str] = []

    # Map measurements by domain
    domain_data: Dict[str, Dict[str, float]] = {}
    met_timestamp = 142.0

    for m in req.measurements:
        # Validate value bounds
        if m.metric_name == "heart_rate" and (m.value < 25 or m.value > 250):
            validation_warnings.append(f"Heart rate value {m.value} bpm is outside physiological human limits (25 - 250).")
        if m.metric_name in ("bp_systolic", "bp_diastolic") and (m.value < 40 or m.value > 300):
            validation_warnings.append(f"Blood pressure {m.metric_name} value {m.value} mmHg is atypical.")
        if m.metric_name == "spo2" and (m.value < 50 or m.value > 100):
            validation_warnings.append(f"SpO2 oxygen saturation {m.value}% is outside plausible range.")

        # Save to checkup_measurements
        crud.add_checkup_measurement(
            session=session,
            checkup_id=checkup.id,
            domain=m.domain,
            metric_name=m.metric_name,
            value=m.value,
            unit=m.unit,
            reference_range=m.reference_range,
            data_source=m.data_source,
        )
        measurements_saved += 1

        # Also register in telemetry and evaluate personal baseline
        crud.create_vital_reading(
            session=session,
            crew_id=target_crew.id,
            metric_name=m.metric_name,
            value=m.value,
            unit=m.unit,
            timestamp_met=met_timestamp,
        )

        deviation = baseline_engine.evaluate(
            session=session,
            crew_id=target_crew.id,
            metric_name=m.metric_name,
            value=m.value,
        )

        if deviation.is_significant:
            hazard = HazardType.GRAVITY if m.domain in ("cardiovascular", "neuromuscular", "sans") else HazardType.IMMUNE
            sev = alert_engine.classify_severity(deviation)
            alert = alert_engine.generate_alert(
                session=session,
                crew_id=target_crew.id,
                hazard=hazard,
                deviation=deviation,
                timestamp_met=met_timestamp,
            )
            sf_queue.enqueue(
                session=session,
                crew_id=target_crew.id,
                alert_id=crud.get_alert_by_uuid(session, alert.alert_id).id,
                timestamp_met=met_timestamp,
                raw_digest=f"Checkup {checkup_id}: {m.metric_name}={m.value} {m.unit}",
            )
        else:
            baseline_engine.update_baseline(
                session=session,
                crew_id=target_crew.id,
                metric_name=m.metric_name,
                new_value=m.value,
                timestamp_met=met_timestamp,
            )

        # Generate insight
        insight_engine.evaluate_deviation(
            session=session,
            crew_id=target_crew.id,
            module=m.domain,
            deviation=deviation,
            subject_id=target_crew.astronaut_id,
        )

        # Collect for module ML inference
        if m.domain not in domain_data:
            domain_data[m.domain] = {}
        domain_data[m.domain][m.metric_name] = m.value

    # 5. Route to ML Analytical Adapters
    for domain, metrics in domain_data.items():
        mod_name = domain.lower()
        if mod_name in ml_router.module_names:
            try:
                pred = ml_router.predict(mod_name, metrics)
                modules_processed.append(mod_name)
                # Store prediction
                crud.create_ml_prediction(
                    session=session,
                    crew_id=target_crew.id,
                    module_name=mod_name,
                    input_summary=f"Checkup {checkup_id}",
                    prediction=pred,
                    confidence=pred.get("confidence", 0.85),
                    timestamp_met=met_timestamp,
                )
                insight_engine.evaluate_ml_prediction(
                    session=session,
                    crew_id=target_crew.id,
                    module=mod_name,
                    prediction=pred,
                    subject_id=target_crew.astronaut_id,
                )
            except Exception as e:
                modules_awaiting.append(f"{mod_name} (ML processing is currently unavailable: {str(e)})")
        else:
            modules_awaiting.append(mod_name)

    session.commit()

    return HealthCheckupSubmissionConfirmation(
        status="Health Checkup Submitted Successfully",
        checkup_id=checkup.checkup_id,
        astronaut_id=target_crew.astronaut_id,
        checkup_date=checkup.checkup_date,
        measurements_saved=measurements_saved,
        files_uploaded=len(checkup.files) if checkup.files else 0,
        modules_processed=modules_processed,
        modules_awaiting=modules_awaiting,
        validation_warnings=validation_warnings,
        record_url=f"#/health-records?id={checkup.checkup_id}",
    )


@router.get("/health-checkups/{checkup_id_or_astronaut_id}")
def get_health_checkups_or_detail(
    checkup_id_or_astronaut_id: str,
    session: Session = Depends(get_db),
):
    """Retrieve either a single checkup by checkup_id or a list of checkups by astronaut_id."""
    # Check if this matches a specific checkup_id (e.g., CHK-...)
    if checkup_id_or_astronaut_id.startswith("CHK-"):
        checkup = crud.get_health_checkup(session, checkup_id_or_astronaut_id)
        if not checkup:
            raise HTTPException(status_code=404, detail="Health checkup record not found")
        crew = checkup.crew_member
        return HealthCheckupDetailResponse(
            id=checkup.id,
            checkup_id=checkup.checkup_id,
            astronaut_id=checkup.astronaut_id,
            crew_name=crew.name if crew else "Astronaut",
            crew_role=crew.role if crew else "Crew",
            checkup_date=checkup.checkup_date,
            checkup_time=checkup.checkup_time,
            location=checkup.location,
            medical_officer=checkup.medical_officer,
            checkup_type=checkup.checkup_type,
            notes=checkup.notes,
            submission_status=checkup.submission_status,
            submitted_by_name=checkup.submitted_by_name,
            is_submitted_by_officer=checkup.is_submitted_by_officer,
            is_amendment=checkup.is_amendment,
            amends_checkup_id=checkup.amends_checkup_id,
            created_at=checkup.created_at.isoformat() if checkup.created_at else "",
            measurements=[
                MeasurementResponseModel(
                    id=m.id,
                    domain=m.domain,
                    metric_name=m.metric_name,
                    value=m.value,
                    unit=m.unit,
                    reference_range=m.reference_range,
                    data_source=m.data_source,
                )
                for m in checkup.measurements
            ],
            files=[
                MedicalFileResponseModel(
                    id=f.id,
                    file_id=f.file_id,
                    original_filename=f.original_filename,
                    health_module=f.health_module,
                    file_size_bytes=f.file_size_bytes,
                    mime_type=f.mime_type,
                    sha256_checksum=f.sha256_checksum,
                    processing_status=f.processing_status,
                    created_at=f.created_at.isoformat() if f.created_at else "",
                )
                for f in checkup.files
            ],
        )

    # Otherwise treat as astronaut_id
    astronaut_id = checkup_id_or_astronaut_id
    records = crud.list_health_checkups_for_astronaut(session, astronaut_id)
    results = []
    for c in records:
        crew = c.crew_member
        results.append(
            HealthCheckupDetailResponse(
                id=c.id,
                checkup_id=c.checkup_id,
                astronaut_id=c.astronaut_id,
                crew_name=crew.name if crew else "Astronaut",
                crew_role=crew.role if crew else "Crew",
                checkup_date=c.checkup_date,
                checkup_time=c.checkup_time,
                location=c.location,
                medical_officer=c.medical_officer,
                checkup_type=c.checkup_type,
                notes=c.notes,
                submission_status=c.submission_status,
                submitted_by_name=c.submitted_by_name,
                is_submitted_by_officer=c.is_submitted_by_officer,
                is_amendment=c.is_amendment,
                amends_checkup_id=c.amends_checkup_id,
                created_at=c.created_at.isoformat() if c.created_at else "",
                measurements=[
                    MeasurementResponseModel(
                        id=m.id,
                        domain=m.domain,
                        metric_name=m.metric_name,
                        value=m.value,
                        unit=m.unit,
                        reference_range=m.reference_range,
                        data_source=m.data_source,
                    )
                    for m in c.measurements
                ],
                files=[
                    MedicalFileResponseModel(
                        id=f.id,
                        file_id=f.file_id,
                        original_filename=f.original_filename,
                        health_module=f.health_module,
                        file_size_bytes=f.file_size_bytes,
                        mime_type=f.mime_type,
                        sha256_checksum=f.sha256_checksum,
                        processing_status=f.processing_status,
                        created_at=f.created_at.isoformat() if f.created_at else "",
                    )
                    for f in c.files
                ],
            )
        )
    return results


@router.put("/health-checkups/{checkup_id}", response_model=HealthCheckupDetailResponse)
def update_or_amend_health_checkup(
    checkup_id: str,
    req: CheckupUpdateRequest,
    current_user: CrewMember = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Update or create an auditable amendment for a finalized checkup."""
    checkup = crud.get_health_checkup(session, checkup_id)
    if not checkup:
        raise HTTPException(status_code=404, detail="Health checkup record not found")

    is_officer = (
        current_user.is_medical_officer
        or any(k in current_user.role.lower() for k in ["medical", "doctor", "surgeon", "physician"])
    )
    if current_user.id != checkup.crew_id and not is_officer:
        raise HTTPException(status_code=403, detail="Permission denied to modify this health record")

    # If already finalized or amended, update notes with audit trail
    audit_note = f"\n[Amendment by {current_user.name} at {datetime.now(timezone.utc).isoformat()}]: {req.amendment_reason or 'Clinical record update'}"
    new_notes = (checkup.notes or "") + audit_note if req.amendment_reason else (req.notes or checkup.notes)

    updated = crud.update_health_checkup(
        session=session,
        checkup_id=checkup_id,
        notes=new_notes,
        medical_officer=req.medical_officer,
        location=req.location,
        submission_status=req.submission_status or "amended",
        is_amendment=True if req.amendment_reason else checkup.is_amendment,
    )
    session.commit()

    crew = updated.crew_member
    return HealthCheckupDetailResponse(
        id=updated.id,
        checkup_id=updated.checkup_id,
        astronaut_id=updated.astronaut_id,
        crew_name=crew.name if crew else "Astronaut",
        crew_role=crew.role if crew else "Crew",
        checkup_date=updated.checkup_date,
        checkup_time=updated.checkup_time,
        location=updated.location,
        medical_officer=updated.medical_officer,
        checkup_type=updated.checkup_type,
        notes=updated.notes,
        submission_status=updated.submission_status,
        submitted_by_name=updated.submitted_by_name,
        is_submitted_by_officer=updated.is_submitted_by_officer,
        is_amendment=updated.is_amendment,
        amends_checkup_id=updated.amends_checkup_id,
        created_at=updated.created_at.isoformat() if updated.created_at else "",
        measurements=[
            MeasurementResponseModel(
                id=m.id,
                domain=m.domain,
                metric_name=m.metric_name,
                value=m.value,
                unit=m.unit,
                reference_range=m.reference_range,
                data_source=m.data_source,
            )
            for m in updated.measurements
        ],
        files=[
            MedicalFileResponseModel(
                id=f.id,
                file_id=f.file_id,
                original_filename=f.original_filename,
                health_module=f.health_module,
                file_size_bytes=f.file_size_bytes,
                mime_type=f.mime_type,
                sha256_checksum=f.sha256_checksum,
                processing_status=f.processing_status,
                created_at=f.created_at.isoformat() if f.created_at else "",
            )
            for f in updated.files
        ],
    )


@router.post("/health-checkups/{checkup_id}/measurements", response_model=List[MeasurementResponseModel])
def add_measurements_to_checkup(
    checkup_id: str,
    measurements: List[MeasurementItem],
    session: Session = Depends(get_db),
    baseline_engine: PersonalBaselineEngine = Depends(get_baseline_engine),
):
    """Add additional discrete measurements to an existing checkup session."""
    checkup = crud.get_health_checkup(session, checkup_id)
    if not checkup:
        raise HTTPException(status_code=404, detail="Health checkup record not found")

    added = []
    for m in measurements:
        rec = crud.add_checkup_measurement(
            session=session,
            checkup_id=checkup.id,
            domain=m.domain,
            metric_name=m.metric_name,
            value=m.value,
            unit=m.unit,
            reference_range=m.reference_range,
            data_source=m.data_source,
        )
        added.append(
            MeasurementResponseModel(
                id=rec.id,
                domain=rec.domain,
                metric_name=rec.metric_name,
                value=rec.value,
                unit=rec.unit,
                reference_range=rec.reference_range,
                data_source=rec.data_source,
            )
        )
    session.commit()
    return added


# ── File Upload & Storage Endpoints ──────────────────────────────────────

@router.post("/health-checkups/{checkup_id}/files", response_model=List[MedicalFileResponseModel])
def upload_medical_files(
    checkup_id: str,
    files: List[UploadFile] = File(...),
    health_module: str = Form("general"),
    session: Session = Depends(get_db),
):
    """Upload supporting medical reports, DICOM/ECG scans, or laboratory documents."""
    checkup = crud.get_health_checkup(session, checkup_id)
    if not checkup:
        raise HTTPException(status_code=404, detail="Target health checkup record not found")

    saved_files = []
    MEDICAL_FILES_DIR.mkdir(parents=True, exist_ok=True)

    for file in files:
        # Validate filename and extension
        filename = file.filename or "medical_report"
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_FILE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension '.{ext}' is not permitted. Allowed: {sorted(list(ALLOWED_FILE_EXTENSIONS))}",
            )

        # Read content synchronously and compute hash
        content = file.file.read()
        file_size = len(content)

        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File '{filename}' exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024*1024)} MB",
            )

        sha256 = hashlib.sha256(content).hexdigest()
        file_id = f"FILE-{uuid.uuid4().hex[:8].upper()}"

        # Safe local filename
        clean_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", filename)
        stored_filename = f"{checkup_id}_{file_id}_{clean_name}"
        disk_path = MEDICAL_FILES_DIR / stored_filename

        with open(disk_path, "wb") as f_out:
            f_out.write(content)

        # Mock OCR / parsing simulation if text/JSON
        extracted_data = {}
        if ext in ("json", "csv"):
            try:
                if ext == "json":
                    extracted_data = json.loads(content.decode("utf-8", errors="ignore"))
                elif ext == "csv":
                    extracted_data = {"type": "tabular_matrix", "lines": len(content.splitlines())}
            except Exception:
                pass

        mf = crud.create_medical_file(
            session=session,
            file_id=file_id,
            checkup_id=checkup.id,
            astronaut_id=checkup.astronaut_id,
            health_module=health_module,
            original_filename=filename,
            stored_filename=stored_filename,
            file_path=str(disk_path),
            file_size_bytes=file_size,
            mime_type=file.content_type or "application/octet-stream",
            sha256_checksum=sha256,
            extracted_data_json=json.dumps(extracted_data),
            processing_status="verified" if extracted_data else "stored",
        )
        saved_files.append(
            MedicalFileResponseModel(
                id=mf.id,
                file_id=mf.file_id,
                original_filename=mf.original_filename,
                health_module=mf.health_module,
                file_size_bytes=mf.file_size_bytes,
                mime_type=mf.mime_type,
                sha256_checksum=mf.sha256_checksum,
                processing_status=mf.processing_status,
                created_at=mf.created_at.isoformat() if mf.created_at else "",
            )
        )

    session.commit()
    return saved_files


@router.get("/medical-files/{file_id}")
def download_medical_file(file_id: str, session: Session = Depends(get_db)):
    """Download stored medical report artifact."""
    mf = crud.get_medical_file(session, file_id)
    if not mf:
        raise HTTPException(status_code=404, detail="Medical file not found")

    file_path = Path(mf.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File on disk has been moved or purged")

    return FileResponse(
        path=str(file_path),
        filename=mf.original_filename,
        media_type=mf.mime_type,
    )


@router.get("/medical-files/{file_id}/status")
def get_medical_file_status(file_id: str, session: Session = Depends(get_db)):
    """Retrieve extraction and processing verification status of uploaded report."""
    mf = crud.get_medical_file(session, file_id)
    if not mf:
        raise HTTPException(status_code=404, detail="Medical file not found")

    return {
        "file_id": mf.file_id,
        "original_filename": mf.original_filename,
        "health_module": mf.health_module,
        "processing_status": mf.processing_status,
        "sha256_checksum": mf.sha256_checksum,
        "file_size_bytes": mf.file_size_bytes,
        "extracted_data": json.loads(mf.extracted_data_json or "{}"),
        "created_at": mf.created_at.isoformat() if mf.created_at else "",
    }


# ── Astronaut Current User History Endpoints ─────────────────────────────

@router.get("/astronauts/me/health-history", response_model=List[HealthCheckupDetailResponse])
def get_my_health_history(
    current_user: CrewMember = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Retrieve checkup records for the authenticated astronaut session."""
    records = crud.list_health_checkups_for_astronaut(session, current_user.astronaut_id)
    results = []
    for c in records:
        crew = c.crew_member
        results.append(
            HealthCheckupDetailResponse(
                id=c.id,
                checkup_id=c.checkup_id,
                astronaut_id=c.astronaut_id,
                crew_name=crew.name if crew else current_user.name,
                crew_role=crew.role if crew else current_user.role,
                checkup_date=c.checkup_date,
                checkup_time=c.checkup_time,
                location=c.location,
                medical_officer=c.medical_officer,
                checkup_type=c.checkup_type,
                notes=c.notes,
                submission_status=c.submission_status,
                submitted_by_name=c.submitted_by_name,
                is_submitted_by_officer=c.is_submitted_by_officer,
                is_amendment=c.is_amendment,
                amends_checkup_id=c.amends_checkup_id,
                created_at=c.created_at.isoformat() if c.created_at else "",
                measurements=[
                    MeasurementResponseModel(
                        id=m.id,
                        domain=m.domain,
                        metric_name=m.metric_name,
                        value=m.value,
                        unit=m.unit,
                        reference_range=m.reference_range,
                        data_source=m.data_source,
                    )
                    for m in c.measurements
                ],
                files=[
                    MedicalFileResponseModel(
                        id=f.id,
                        file_id=f.file_id,
                        original_filename=f.original_filename,
                        health_module=f.health_module,
                        file_size_bytes=f.file_size_bytes,
                        mime_type=f.mime_type,
                        sha256_checksum=f.sha256_checksum,
                        processing_status=f.processing_status,
                        created_at=f.created_at.isoformat() if f.created_at else "",
                    )
                    for f in c.files
                ],
            )
        )
    return results


@router.get("/astronauts/me/latest-checkup", response_model=Optional[HealthCheckupDetailResponse])
def get_my_latest_checkup(
    current_user: CrewMember = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Retrieve the most recent checkup for the authenticated astronaut."""
    latest = crud.get_latest_health_checkup_for_astronaut(session, current_user.astronaut_id)
    if not latest:
        return None
    crew = latest.crew_member
    return HealthCheckupDetailResponse(
        id=latest.id,
        checkup_id=latest.checkup_id,
        astronaut_id=latest.astronaut_id,
        crew_name=crew.name if crew else current_user.name,
        crew_role=crew.role if crew else current_user.role,
        checkup_date=latest.checkup_date,
        checkup_time=latest.checkup_time,
        location=latest.location,
        medical_officer=latest.medical_officer,
        checkup_type=latest.checkup_type,
        notes=latest.notes,
        submission_status=latest.submission_status,
        submitted_by_name=latest.submitted_by_name,
        is_submitted_by_officer=latest.is_submitted_by_officer,
        is_amendment=latest.is_amendment,
        amends_checkup_id=latest.amends_checkup_id,
        created_at=latest.created_at.isoformat() if latest.created_at else "",
        measurements=[
            MeasurementResponseModel(
                id=m.id,
                domain=m.domain,
                metric_name=m.metric_name,
                value=m.value,
                unit=m.unit,
                reference_range=m.reference_range,
                data_source=m.data_source,
            )
            for m in latest.measurements
        ],
        files=[
            MedicalFileResponseModel(
                id=f.id,
                file_id=f.file_id,
                original_filename=f.original_filename,
                health_module=f.health_module,
                file_size_bytes=f.file_size_bytes,
                mime_type=f.mime_type,
                sha256_checksum=f.sha256_checksum,
                processing_status=f.processing_status,
                created_at=f.created_at.isoformat() if f.created_at else "",
            )
            for f in latest.files
        ],
    )
