"""CRUD operations for ASTRA-MED database models."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from astra_med.db.models import (
    ActionCardRecord,
    ActionTaskRecord,
    AlertRecord,
    CheckupMeasurementRecord,
    CrewMember,
    EncounterPackageRecord,
    GroundReviewRecord,
    HealthCheckupRecord,
    InsightRecord,
    MedicalFileRecord,
    MedicalReportRecord,
    MLPredictionRecord,
    PersonalBaselineRecord,
    VitalReading,
)


# ── CrewMember CRUD ──────────────────────────────────────────────────────

def create_crew_member(
    session: Session,
    name: str,
    role: str,
    status: str = "active",
    astronaut_id: Optional[str] = None,
    mission_id: str = "ASTRA-1",
    username: Optional[str] = None,
    password_hash: Optional[str] = None,
    is_medical_officer: bool = False,
) -> CrewMember:
    # Auto-generate astronaut_id if not supplied
    if not astronaut_id:
        count = session.execute(select(func.count(CrewMember.id))).scalar_one() or 0
        astronaut_id = f"ASTRA-{count + 1:03d}"

    member = CrewMember(
        name=name,
        role=role,
        status=status,
        astronaut_id=astronaut_id,
        mission_id=mission_id,
        username=username,
        password_hash=password_hash,
        is_medical_officer=is_medical_officer,
    )
    session.add(member)
    session.flush()
    return member


def get_crew_by_astronaut_id(session: Session, astronaut_id: str) -> Optional[CrewMember]:
    # Support numeric ID lookup as fallback
    if astronaut_id.isdigit():
        member = session.get(CrewMember, int(astronaut_id))
        if member:
            return member
    stmt = select(CrewMember).where(CrewMember.astronaut_id == astronaut_id)
    member = session.execute(stmt).scalar_one_or_none()
    if not member and astronaut_id.startswith("ASTRA-"):
        try:
            num = int(astronaut_id.split("-")[1])
            fallback_member = session.get(CrewMember, num)
            if fallback_member and (fallback_member.astronaut_id == astronaut_id or not fallback_member.astronaut_id):
                member = fallback_member
        except Exception:
            pass
    return member


def get_crew_by_username(session: Session, username: str) -> Optional[CrewMember]:
    stmt = select(CrewMember).where(CrewMember.username == username)
    return session.execute(stmt).scalar_one_or_none()


def get_crew_member(session: Session, crew_id: int) -> Optional[CrewMember]:
    return session.get(CrewMember, crew_id)


def list_crew_members(session: Session) -> Sequence[CrewMember]:
    result = session.execute(select(CrewMember).order_by(CrewMember.id))
    return result.scalars().all()


# ── VitalReading CRUD ────────────────────────────────────────────────────

def create_vital_reading(
    session: Session,
    crew_id: int,
    metric_name: str,
    value: float,
    unit: str,
    timestamp_met: float,
    sample_type: str = "continuous",
    sqi_score: float = 1.0,
    sqi_valid: bool = True,
    flags: Optional[dict] = None,
) -> VitalReading:
    reading = VitalReading(
        crew_id=crew_id,
        metric_name=metric_name,
        value=value,
        unit=unit,
        timestamp_met=timestamp_met,
        sample_type=sample_type,
        sqi_score=sqi_score,
        sqi_valid=sqi_valid,
        flags_json=json.dumps(flags or {}),
    )
    session.add(reading)
    session.flush()
    return reading


def get_vitals_for_crew(
    session: Session,
    crew_id: int,
    metric_name: Optional[str] = None,
    limit: int = 100,
) -> Sequence[VitalReading]:
    stmt = select(VitalReading).where(VitalReading.crew_id == crew_id)
    if metric_name:
        stmt = stmt.where(VitalReading.metric_name == metric_name)
    stmt = stmt.order_by(VitalReading.timestamp_met.desc()).limit(limit)
    result = session.execute(stmt)
    return result.scalars().all()


def get_latest_vitals(
    session: Session,
    crew_id: int,
) -> Sequence[VitalReading]:
    """Get the latest reading for each metric for a crew member."""
    subq = (
        select(
            VitalReading.metric_name,
            func.max(VitalReading.timestamp_met).label("max_met"),
        )
        .where(VitalReading.crew_id == crew_id)
        .group_by(VitalReading.metric_name)
        .subquery()
    )
    stmt = (
        select(VitalReading)
        .join(
            subq,
            (VitalReading.metric_name == subq.c.metric_name)
            & (VitalReading.timestamp_met == subq.c.max_met)
            & (VitalReading.crew_id == crew_id),
        )
    )
    result = session.execute(stmt)
    return result.scalars().all()


# ── PersonalBaselineRecord CRUD ──────────────────────────────────────────

def upsert_baseline(
    session: Session,
    crew_id: int,
    metric_name: str,
    mean: float,
    std: float,
    n_samples: int,
    frozen: bool = False,
    last_updated_met: float = 0.0,
) -> PersonalBaselineRecord:
    stmt = select(PersonalBaselineRecord).where(
        PersonalBaselineRecord.crew_id == crew_id,
        PersonalBaselineRecord.metric_name == metric_name,
    )
    record = session.execute(stmt).scalar_one_or_none()

    if record is None:
        record = PersonalBaselineRecord(
            crew_id=crew_id,
            metric_name=metric_name,
            mean=mean,
            std=std,
            n_samples=n_samples,
            frozen=frozen,
            last_updated_met=last_updated_met,
        )
        session.add(record)
    else:
        record.mean = mean
        record.std = std
        record.n_samples = n_samples
        record.frozen = frozen
        record.last_updated_met = last_updated_met

    session.flush()
    return record


def get_baseline(
    session: Session,
    crew_id: int,
    metric_name: str,
) -> Optional[PersonalBaselineRecord]:
    stmt = select(PersonalBaselineRecord).where(
        PersonalBaselineRecord.crew_id == crew_id,
        PersonalBaselineRecord.metric_name == metric_name,
    )
    return session.execute(stmt).scalar_one_or_none()


def get_all_baselines_for_crew(
    session: Session,
    crew_id: int,
) -> Sequence[PersonalBaselineRecord]:
    stmt = select(PersonalBaselineRecord).where(
        PersonalBaselineRecord.crew_id == crew_id
    ).order_by(PersonalBaselineRecord.metric_name)
    return session.execute(stmt).scalars().all()


def freeze_baseline(
    session: Session,
    crew_id: int,
    metric_name: str,
) -> bool:
    baseline = get_baseline(session, crew_id, metric_name)
    if baseline:
        baseline.frozen = True
        session.flush()
        return True
    return False


def unfreeze_baseline(
    session: Session,
    crew_id: int,
    metric_name: str,
) -> bool:
    baseline = get_baseline(session, crew_id, metric_name)
    if baseline:
        baseline.frozen = False
        session.flush()
        return True
    return False


# ── AlertRecord CRUD ─────────────────────────────────────────────────────

def create_alert(
    session: Session,
    crew_id: int,
    hazard: str,
    severity: str,
    functional_status: str,
    timestamp_met: float,
    metric_name: str,
    observed_value: float,
    baseline_mean: float = 0.0,
    baseline_std: float = 0.0,
    z_score: float = 0.0,
    direction: str = "NORMAL",
    summary_text: str = "",
    action_card_id: Optional[str] = None,
) -> AlertRecord:
    import uuid
    alert_uuid = f"alt-{uuid.uuid4().hex[:12]}"
    alert = AlertRecord(
        alert_uuid=alert_uuid,
        crew_id=crew_id,
        hazard=hazard,
        severity=severity,
        functional_status=functional_status,
        timestamp_met=timestamp_met,
        metric_name=metric_name,
        observed_value=observed_value,
        baseline_mean=baseline_mean,
        baseline_std=baseline_std,
        z_score=z_score,
        direction=direction,
        summary_text=summary_text,
        action_card_id=action_card_id,
        acknowledged=False,
    )
    session.add(alert)
    session.flush()
    return alert


def get_alert(session: Session, alert_id: int) -> Optional[AlertRecord]:
    return session.get(AlertRecord, alert_id)


def get_alert_by_uuid(session: Session, alert_uuid: str) -> Optional[AlertRecord]:
    stmt = select(AlertRecord).where(AlertRecord.alert_uuid == alert_uuid)
    return session.execute(stmt).scalar_one_or_none()


def get_alerts(
    session: Session,
    crew_id: Optional[int] = None,
    severity: Optional[str] = None,
    hazard: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = 50,
) -> Sequence[AlertRecord]:
    stmt = select(AlertRecord)
    if crew_id is not None:
        stmt = stmt.where(AlertRecord.crew_id == crew_id)
    if severity:
        stmt = stmt.where(AlertRecord.severity == severity)
    if hazard:
        stmt = stmt.where(AlertRecord.hazard == hazard)
    if acknowledged is not None:
        stmt = stmt.where(AlertRecord.acknowledged == acknowledged)
    stmt = stmt.order_by(AlertRecord.timestamp_met.desc()).limit(limit)
    return session.execute(stmt).scalars().all()


def get_active_alerts(
    session: Session,
    crew_id: Optional[int] = None,
) -> Sequence[AlertRecord]:
    stmt = select(AlertRecord).where(AlertRecord.acknowledged == False)
    if crew_id is not None:
        stmt = stmt.where(AlertRecord.crew_id == crew_id)
    stmt = stmt.order_by(AlertRecord.timestamp_met.desc())
    return session.execute(stmt).scalars().all()


def acknowledge_alert(session: Session, alert_id: int) -> Optional[AlertRecord]:
    alert = session.get(AlertRecord, alert_id)
    if alert:
        alert.acknowledged = True
        session.flush()
    return alert


# ── ActionCardRecord CRUD ────────────────────────────────────────────────

def create_action_card(
    session: Session,
    card_id: str,
    version: str,
    hazard: str,
    severity: str,
    title: str,
    summary: str = "",
    instructions: Optional[list] = None,
    safety_limits: Optional[dict] = None,
    de_escalation_criteria: str = "",
) -> ActionCardRecord:
    card = ActionCardRecord(
        card_id=card_id,
        version=version,
        hazard=hazard,
        severity=severity,
        title=title,
        summary=summary,
        instructions_json=json.dumps(instructions or []),
        safety_limits_json=json.dumps(safety_limits or {}),
        de_escalation_criteria=de_escalation_criteria,
    )
    session.add(card)
    session.flush()
    return card


def get_action_card(session: Session, card_id: str) -> Optional[ActionCardRecord]:
    stmt = select(ActionCardRecord).where(ActionCardRecord.card_id == card_id)
    return session.execute(stmt).scalar_one_or_none()


def list_action_cards(
    session: Session,
    hazard: Optional[str] = None,
    severity: Optional[str] = None,
) -> Sequence[ActionCardRecord]:
    stmt = select(ActionCardRecord)
    if hazard:
        stmt = stmt.where(ActionCardRecord.hazard == hazard)
    if severity:
        stmt = stmt.where(ActionCardRecord.severity == severity)
    return session.execute(stmt).scalars().all()


# ── EncounterPackageRecord CRUD ──────────────────────────────────────────

def create_encounter(
    session: Session,
    encounter_uuid: str,
    crew_id: int,
    alert_id: int,
    timestamp_met: float,
    action_card_id: Optional[str] = None,
    raw_digest: str = "",
    crew_acknowledged: bool = False,
    checksum: str = "",
) -> EncounterPackageRecord:
    encounter = EncounterPackageRecord(
        encounter_uuid=encounter_uuid,
        crew_id=crew_id,
        alert_id=alert_id,
        timestamp_met=timestamp_met,
        action_card_id=action_card_id,
        raw_digest=raw_digest,
        crew_acknowledged=crew_acknowledged,
        ground_synced=False,
        checksum=checksum,
    )
    session.add(encounter)
    session.flush()
    return encounter


def get_encounter_by_id(session: Session, encounter_id: int) -> Optional[EncounterPackageRecord]:
    return session.get(EncounterPackageRecord, encounter_id)


def get_pending_encounters(session: Session) -> Sequence[EncounterPackageRecord]:
    stmt = (
        select(EncounterPackageRecord)
        .where(EncounterPackageRecord.ground_synced == False)
        .order_by(EncounterPackageRecord.timestamp_met)
    )
    return session.execute(stmt).scalars().all()


def mark_encounter_synced(session: Session, encounter_id: int) -> bool:
    encounter = session.get(EncounterPackageRecord, encounter_id)
    if encounter:
        encounter.ground_synced = True
        session.flush()
        return True
    return False


# ── GroundReviewRecord CRUD ──────────────────────────────────────────────

def create_ground_review(
    session: Session,
    encounter_id: int,
    reviewer: str,
    review_text: str = "",
    recommendations: Optional[list] = None,
    approved_updates: Optional[dict] = None,
    received_met: float = 0.0,
) -> GroundReviewRecord:
    review = GroundReviewRecord(
        encounter_id=encounter_id,
        reviewer=reviewer,
        review_text=review_text,
        recommendations_json=json.dumps(recommendations or []),
        approved_updates_json=json.dumps(approved_updates or {}),
        received_met=received_met,
        applied=False,
    )
    session.add(review)
    session.flush()
    return review


def get_reviews_for_encounter(
    session: Session,
    encounter_id: int,
) -> Sequence[GroundReviewRecord]:
    stmt = (
        select(GroundReviewRecord)
        .where(GroundReviewRecord.encounter_id == encounter_id)
        .order_by(GroundReviewRecord.created_at)
    )
    return session.execute(stmt).scalars().all()


# ── MLPrediction CRUD ────────────────────────────────────────────────────

def create_ml_prediction(
    session: Session,
    crew_id: int,
    module_name: str,
    input_summary: str = "",
    prediction: Optional[dict] = None,
    confidence: float = 0.0,
    timestamp_met: float = 0.0,
) -> MLPredictionRecord:
    record = MLPredictionRecord(
        crew_id=crew_id,
        module_name=module_name,
        input_summary=input_summary,
        prediction_json=json.dumps(prediction or {}),
        confidence=confidence,
        timestamp_met=timestamp_met,
    )
    session.add(record)
    session.flush()
    return record


def get_predictions_for_crew(
    session: Session,
    crew_id: int,
    module_name: Optional[str] = None,
    limit: int = 50,
) -> Sequence[MLPredictionRecord]:
    stmt = select(MLPredictionRecord).where(MLPredictionRecord.crew_id == crew_id)
    if module_name:
        stmt = stmt.where(MLPredictionRecord.module_name == module_name)
    stmt = stmt.order_by(MLPredictionRecord.timestamp_met.desc()).limit(limit)
    return session.execute(stmt).scalars().all()


# ── InsightRecord CRUD ───────────────────────────────────────────────────

def create_insight(
    session: Session,
    subject_id: str,
    crew_id: int,
    module: str,
    observation: str,
    severity: str = "monitor",
    baseline_deviation_detected: bool = False,
    diagnosis: Optional[str] = None,
    requires_medical_review: bool = False,
    metric_name: Optional[str] = None,
    observed_value: Optional[float] = None,
    baseline_mean: Optional[float] = None,
    z_score: Optional[float] = None,
) -> InsightRecord:
    rec = InsightRecord(
        subject_id=subject_id,
        crew_id=crew_id,
        module=module,
        observation=observation,
        severity=severity,
        baseline_deviation_detected=baseline_deviation_detected,
        diagnosis=diagnosis,  # strictly null in clinical practice
        requires_medical_review=requires_medical_review,
        metric_name=metric_name,
        observed_value=observed_value,
        baseline_mean=baseline_mean,
        z_score=z_score,
        acknowledged=False,
    )
    session.add(rec)
    session.flush()
    return rec


def get_insights_for_crew(
    session: Session,
    crew_id: int,
    limit: int = 50,
) -> Sequence[InsightRecord]:
    stmt = (
        select(InsightRecord)
        .where(InsightRecord.crew_id == crew_id)
        .order_by(InsightRecord.created_at.desc())
        .limit(limit)
    )
    return session.execute(stmt).scalars().all()


def list_insights(
    session: Session,
    crew_id: Optional[int] = None,
    severity: Optional[str] = None,
    module: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = 100,
) -> Sequence[InsightRecord]:
    stmt = select(InsightRecord)
    if crew_id is not None:
        stmt = stmt.where(InsightRecord.crew_id == crew_id)
    if severity:
        stmt = stmt.where(InsightRecord.severity == severity)
    if module:
        stmt = stmt.where(InsightRecord.module == module)
    if acknowledged is not None:
        stmt = stmt.where(InsightRecord.acknowledged == acknowledged)
    stmt = stmt.order_by(InsightRecord.created_at.desc()).limit(limit)
    return session.execute(stmt).scalars().all()


def acknowledge_insight(session: Session, insight_id: int) -> Optional[InsightRecord]:
    rec = session.get(InsightRecord, insight_id)
    if rec:
        rec.acknowledged = True
        session.flush()
    return rec


# ── ActionTaskRecord CRUD ────────────────────────────────────────────────

def create_action_task(
    session: Session,
    action_id: str,
    crew_id: int,
    title: str,
    description: str,
    source: str = "preapproved_action_library",
    approval_required: bool = False,
    status: str = "pending",
    notes: Optional[str] = None,
) -> ActionTaskRecord:
    task = ActionTaskRecord(
        action_id=action_id,
        crew_id=crew_id,
        title=title,
        description=description,
        source=source,
        approval_required=approval_required,
        status=status,
        notes=notes,
    )
    session.add(task)
    session.flush()
    return task


def list_action_tasks_for_crew(
    session: Session,
    crew_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100,
) -> Sequence[ActionTaskRecord]:
    stmt = select(ActionTaskRecord)
    if crew_id is not None:
        stmt = stmt.where(ActionTaskRecord.crew_id == crew_id)
    if status:
        stmt = stmt.where(ActionTaskRecord.status == status)
    stmt = stmt.order_by(ActionTaskRecord.created_at.desc()).limit(limit)
    return session.execute(stmt).scalars().all()


def get_action_task(session: Session, task_id_or_action_id: str) -> Optional[ActionTaskRecord]:
    if task_id_or_action_id.isdigit():
        task = session.get(ActionTaskRecord, int(task_id_or_action_id))
        if task:
            return task
    stmt = (
        select(ActionTaskRecord)
        .where(ActionTaskRecord.action_id == task_id_or_action_id)
        .order_by(ActionTaskRecord.created_at.desc())
    )
    return session.execute(stmt).scalars().first()


def acknowledge_action_task(
    session: Session,
    action_id: str,
    notes: Optional[str] = None,
) -> Optional[ActionTaskRecord]:
    task = get_action_task(session, action_id)
    if task:
        task.status = "acknowledged"
        task.acknowledged_at = datetime.now(timezone.utc)
        if notes:
            task.notes = notes
        session.flush()
    return task


# ── MedicalReportRecord CRUD ─────────────────────────────────────────────

def create_medical_report(
    session: Session,
    report_id: str,
    crew_id: int,
    title: str,
    summary: str,
    domain: str = "general",
    status: str = "queued_for_sync",
    requires_physician_review: bool = True,
    future_phase_updates: Optional[dict] = None,
    checksum: str = "",
) -> MedicalReportRecord:
    rep = MedicalReportRecord(
        report_id=report_id,
        crew_id=crew_id,
        title=title,
        summary=summary,
        domain=domain,
        status=status,
        requires_physician_review=requires_physician_review,
        future_phase_updates_json=json.dumps(future_phase_updates or {}),
        checksum=checksum,
    )
    session.add(rep)
    session.flush()
    return rep


def get_medical_reports_for_crew(
    session: Session,
    crew_id: Optional[int] = None,
    status: Optional[str] = None,
) -> Sequence[MedicalReportRecord]:
    stmt = select(MedicalReportRecord)
    if crew_id is not None:
        stmt = stmt.where(MedicalReportRecord.crew_id == crew_id)
    if status:
        stmt = stmt.where(MedicalReportRecord.status == status)
    stmt = stmt.order_by(MedicalReportRecord.created_at.desc())
    return session.execute(stmt).scalars().all()


def get_medical_report(session: Session, report_id: str) -> Optional[MedicalReportRecord]:
    stmt = select(MedicalReportRecord).where(MedicalReportRecord.report_id == report_id)
    return session.execute(stmt).scalar_one_or_none()


def mark_medical_report_synced(session: Session, report_id: str) -> Optional[MedicalReportRecord]:
    rep = get_medical_report(session, report_id)
    if rep:
        rep.status = "transmitted"
        rep.synced_at = datetime.now(timezone.utc)
        session.flush()
    return rep


def review_medical_report(
    session: Session,
    report_id: str,
    physician_decision: str,
    comments: str,
    future_phase_updates: Optional[dict] = None,
) -> Optional[MedicalReportRecord]:
    rep = get_medical_report(session, report_id)
    if rep:
        rep.status = "reviewed"
        rep.physician_decision = physician_decision
        rep.physician_comments = comments
        if future_phase_updates is not None:
            rep.future_phase_updates_json = json.dumps(future_phase_updates)
        session.flush()
    return rep


# ── HealthCheckupRecord CRUD ─────────────────────────────────────────────

def create_health_checkup(
    session: Session,
    checkup_id: str,
    astronaut_id: str,
    crew_id: int,
    checkup_date: str,
    checkup_type: str,
    checkup_time: Optional[str] = None,
    location: Optional[str] = None,
    medical_officer: Optional[str] = None,
    notes: Optional[str] = None,
    submitted_by_crew_id: Optional[int] = None,
    submitted_by_name: Optional[str] = None,
    is_submitted_by_officer: bool = False,
    idempotency_key: Optional[str] = None,
    is_amendment: bool = False,
    amends_checkup_id: Optional[str] = None,
) -> HealthCheckupRecord:
    # Prevent duplicate submissions with idempotency key
    if idempotency_key:
        stmt = select(HealthCheckupRecord).where(HealthCheckupRecord.idempotency_key == idempotency_key)
        existing = session.execute(stmt).scalar_one_or_none()
        if existing:
            return existing

    rec = HealthCheckupRecord(
        checkup_id=checkup_id,
        astronaut_id=astronaut_id,
        crew_id=crew_id,
        checkup_date=checkup_date,
        checkup_type=checkup_type,
        checkup_time=checkup_time,
        location=location,
        medical_officer=medical_officer,
        notes=notes,
        submitted_by_crew_id=submitted_by_crew_id,
        submitted_by_name=submitted_by_name,
        is_submitted_by_officer=is_submitted_by_officer,
        idempotency_key=idempotency_key,
        is_amendment=is_amendment,
        amends_checkup_id=amends_checkup_id,
        submission_status="submitted",
    )
    session.add(rec)
    session.flush()
    return rec


def get_health_checkup(session: Session, checkup_id_or_id: str | int) -> Optional[HealthCheckupRecord]:
    if isinstance(checkup_id_or_id, int) or (isinstance(checkup_id_or_id, str) and checkup_id_or_id.isdigit()):
        rec = session.get(HealthCheckupRecord, int(checkup_id_or_id))
        if rec:
            return rec
    stmt = select(HealthCheckupRecord).where(HealthCheckupRecord.checkup_id == str(checkup_id_or_id))
    return session.execute(stmt).scalar_one_or_none()


def get_health_checkup_by_idempotency_key(session: Session, idempotency_key: str) -> Optional[HealthCheckupRecord]:
    stmt = select(HealthCheckupRecord).where(HealthCheckupRecord.idempotency_key == idempotency_key)
    return session.execute(stmt).scalar_one_or_none()


def list_health_checkups_for_astronaut(
    session: Session,
    astronaut_id: str,
    limit: int = 50,
) -> Sequence[HealthCheckupRecord]:
    crew = get_crew_by_astronaut_id(session, astronaut_id)
    stmt = select(HealthCheckupRecord)
    if crew:
        stmt = stmt.where(HealthCheckupRecord.crew_id == crew.id)
    else:
        stmt = stmt.where(HealthCheckupRecord.astronaut_id == astronaut_id)
    stmt = stmt.order_by(HealthCheckupRecord.created_at.desc()).limit(limit)
    return session.execute(stmt).scalars().all()


def get_latest_health_checkup_for_astronaut(
    session: Session,
    astronaut_id: str,
) -> Optional[HealthCheckupRecord]:
    checkups = list_health_checkups_for_astronaut(session, astronaut_id, limit=1)
    return checkups[0] if checkups else None


def update_health_checkup(
    session: Session,
    checkup_id: str,
    notes: Optional[str] = None,
    medical_officer: Optional[str] = None,
    location: Optional[str] = None,
    submission_status: Optional[str] = None,
    is_amendment: Optional[bool] = None,
) -> Optional[HealthCheckupRecord]:
    rec = get_health_checkup(session, checkup_id)
    if not rec:
        return None
    if notes is not None:
        rec.notes = notes
    if medical_officer is not None:
        rec.medical_officer = medical_officer
    if location is not None:
        rec.location = location
    if submission_status is not None:
        rec.submission_status = submission_status
    if is_amendment is not None:
        rec.is_amendment = is_amendment
    session.flush()
    return rec


# ── CheckupMeasurementRecord CRUD ─────────────────────────────────────────

def add_checkup_measurement(
    session: Session,
    checkup_id: int,
    domain: str,
    metric_name: str,
    value: float,
    unit: str,
    reference_range: Optional[str] = None,
    data_source: str = "manual_entry",
    is_verified: bool = True,
) -> CheckupMeasurementRecord:
    m = CheckupMeasurementRecord(
        checkup_id=checkup_id,
        domain=domain,
        metric_name=metric_name,
        value=value,
        unit=unit,
        reference_range=reference_range,
        data_source=data_source,
        is_verified=is_verified,
    )
    session.add(m)
    session.flush()
    return m


def get_checkup_measurements(
    session: Session,
    checkup_id: int,
) -> Sequence[CheckupMeasurementRecord]:
    stmt = (
        select(CheckupMeasurementRecord)
        .where(CheckupMeasurementRecord.checkup_id == checkup_id)
        .order_by(CheckupMeasurementRecord.domain, CheckupMeasurementRecord.metric_name)
    )
    return session.execute(stmt).scalars().all()


# ── MedicalFileRecord CRUD ───────────────────────────────────────────────

def create_medical_file(
    session: Session,
    file_id: str,
    checkup_id: int,
    astronaut_id: str,
    original_filename: str,
    stored_filename: str,
    file_path: str,
    file_size_bytes: int,
    mime_type: str,
    sha256_checksum: str,
    health_module: str = "general",
    extracted_data_json: str = "{}",
    processing_status: str = "stored",
) -> MedicalFileRecord:
    mf = MedicalFileRecord(
        file_id=file_id,
        checkup_id=checkup_id,
        astronaut_id=astronaut_id,
        health_module=health_module,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=file_path,
        file_size_bytes=file_size_bytes,
        mime_type=mime_type,
        sha256_checksum=sha256_checksum,
        extracted_data_json=extracted_data_json,
        processing_status=processing_status,
    )
    session.add(mf)
    session.flush()
    return mf


def get_medical_file(session: Session, file_id: str) -> Optional[MedicalFileRecord]:
    stmt = select(MedicalFileRecord).where(MedicalFileRecord.file_id == file_id)
    return session.execute(stmt).scalar_one_or_none()


def get_medical_files_for_checkup(
    session: Session,
    checkup_id: int,
) -> Sequence[MedicalFileRecord]:
    stmt = select(MedicalFileRecord).where(MedicalFileRecord.checkup_id == checkup_id)
    return session.execute(stmt).scalars().all()


def update_medical_file_status(
    session: Session,
    file_id: str,
    status: str,
    extracted_data: Optional[dict] = None,
) -> Optional[MedicalFileRecord]:
    mf = get_medical_file(session, file_id)
    if mf:
        mf.processing_status = status
        if extracted_data is not None:
            mf.extracted_data_json = json.dumps(extracted_data)
        session.flush()
    return mf

