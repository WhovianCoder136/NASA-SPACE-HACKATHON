"""SQLAlchemy 2.0 ORM models for ASTRA-MED."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Application-wide declarative base."""
    pass


# ── CrewMember ───────────────────────────────────────────────────────────

class CrewMember(Base):
    __tablename__ = "crew_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    astronaut_id: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, default="ASTRA-001")
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(120), nullable=False)
    mission_id: Mapped[str] = mapped_column(String(30), default="ASTRA-1")
    status: Mapped[str] = mapped_column(String(20), default="active")
    username: Mapped[Optional[str]] = mapped_column(String(60), unique=True, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_medical_officer: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    vitals: Mapped[list["VitalReading"]] = relationship(back_populates="crew_member")
    baselines: Mapped[list["PersonalBaselineRecord"]] = relationship(back_populates="crew_member")
    alerts: Mapped[list["AlertRecord"]] = relationship(back_populates="crew_member")
    encounters: Mapped[list["EncounterPackageRecord"]] = relationship(back_populates="crew_member")
    predictions: Mapped[list["MLPredictionRecord"]] = relationship(back_populates="crew_member")
    insights: Mapped[list["InsightRecord"]] = relationship(back_populates="crew_member")
    action_tasks: Mapped[list["ActionTaskRecord"]] = relationship(back_populates="crew_member")
    medical_reports: Mapped[list["MedicalReportRecord"]] = relationship(back_populates="crew_member")
    checkups: Mapped[list["HealthCheckupRecord"]] = relationship(
        foreign_keys="[HealthCheckupRecord.crew_id]",
        back_populates="crew_member"
    )


# ── VitalReading ─────────────────────────────────────────────────────────

class VitalReading(Base):
    __tablename__ = "vital_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crew_id: Mapped[int] = mapped_column(Integer, ForeignKey("crew_members.id"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    timestamp_met: Mapped[float] = mapped_column(Float, nullable=False)
    sample_type: Mapped[str] = mapped_column(String(20), default="continuous")
    sqi_score: Mapped[float] = mapped_column(Float, default=1.0)
    sqi_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    flags_json: Mapped[Optional[str]] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    crew_member: Mapped["CrewMember"] = relationship(back_populates="vitals")


# ── PersonalBaselineRecord ───────────────────────────────────────────────

class PersonalBaselineRecord(Base):
    __tablename__ = "personal_baselines"
    __table_args__ = (
        UniqueConstraint("crew_id", "metric_name", name="uq_baseline_crew_metric"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crew_id: Mapped[int] = mapped_column(Integer, ForeignKey("crew_members.id"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(80), nullable=False)
    mean: Mapped[float] = mapped_column(Float, default=0.0)
    std: Mapped[float] = mapped_column(Float, default=0.0)
    n_samples: Mapped[int] = mapped_column(Integer, default=0)
    frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    last_updated_met: Mapped[float] = mapped_column(Float, default=0.0)

    crew_member: Mapped["CrewMember"] = relationship(back_populates="baselines")


# ── AlertRecord ──────────────────────────────────────────────────────────

class AlertRecord(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_uuid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    crew_id: Mapped[int] = mapped_column(Integer, ForeignKey("crew_members.id"), nullable=False)
    hazard: Mapped[str] = mapped_column(String(60), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)  # GREEN / AMBER / RED
    functional_status: Mapped[str] = mapped_column(String(20), default="NOMINAL")
    timestamp_met: Mapped[float] = mapped_column(Float, nullable=False)
    metric_name: Mapped[str] = mapped_column(String(80), nullable=False)
    observed_value: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_mean: Mapped[float] = mapped_column(Float, default=0.0)
    baseline_std: Mapped[float] = mapped_column(Float, default=0.0)
    z_score: Mapped[float] = mapped_column(Float, default=0.0)
    direction: Mapped[str] = mapped_column(String(10), default="NORMAL")
    summary_text: Mapped[str] = mapped_column(Text, default="")
    action_card_id: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    crew_member: Mapped["CrewMember"] = relationship(back_populates="alerts")
    encounters: Mapped[list["EncounterPackageRecord"]] = relationship(back_populates="alert")


# ── ActionCardRecord ─────────────────────────────────────────────────────

class ActionCardRecord(Base):
    __tablename__ = "action_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    version: Mapped[str] = mapped_column(String(10), default="1.0")
    hazard: Mapped[str] = mapped_column(String(60), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    instructions_json: Mapped[str] = mapped_column(Text, default="[]")
    safety_limits_json: Mapped[str] = mapped_column(Text, default="{}")
    de_escalation_criteria: Mapped[str] = mapped_column(Text, default="")


# ── EncounterPackageRecord ───────────────────────────────────────────────

class EncounterPackageRecord(Base):
    __tablename__ = "encounter_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    encounter_uuid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    crew_id: Mapped[int] = mapped_column(Integer, ForeignKey("crew_members.id"), nullable=False)
    timestamp_met: Mapped[float] = mapped_column(Float, nullable=False)
    alert_id: Mapped[int] = mapped_column(Integer, ForeignKey("alerts.id"), nullable=False)
    action_card_id: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    raw_digest: Mapped[str] = mapped_column(Text, default="")
    crew_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    ground_synced: Mapped[bool] = mapped_column(Boolean, default=False)
    checksum: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    crew_member: Mapped["CrewMember"] = relationship(back_populates="encounters")
    alert: Mapped["AlertRecord"] = relationship(back_populates="encounters")
    reviews: Mapped[list["GroundReviewRecord"]] = relationship(back_populates="encounter")


# ── GroundReviewRecord ───────────────────────────────────────────────────

class GroundReviewRecord(Base):
    __tablename__ = "ground_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    encounter_id: Mapped[int] = mapped_column(Integer, ForeignKey("encounter_packages.id"), nullable=False)
    reviewer: Mapped[str] = mapped_column(String(120), nullable=False)
    review_text: Mapped[str] = mapped_column(Text, default="")
    recommendations_json: Mapped[str] = mapped_column(Text, default="[]")
    approved_updates_json: Mapped[str] = mapped_column(Text, default="{}")
    received_met: Mapped[float] = mapped_column(Float, default=0.0)
    applied: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    encounter: Mapped["EncounterPackageRecord"] = relationship(back_populates="reviews")


# ── MLPredictionRecord ───────────────────────────────────────────────────

class MLPredictionRecord(Base):
    __tablename__ = "ml_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crew_id: Mapped[int] = mapped_column(Integer, ForeignKey("crew_members.id"), nullable=False)
    module_name: Mapped[str] = mapped_column(String(60), nullable=False)
    input_summary: Mapped[str] = mapped_column(Text, default="")
    prediction_json: Mapped[str] = mapped_column(Text, default="{}")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    timestamp_met: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    crew_member: Mapped["CrewMember"] = relationship(back_populates="predictions")


# ── InsightRecord ────────────────────────────────────────────────────────

class InsightRecord(Base):
    """Clinical & physiological insights generated by the Insight Engine."""
    __tablename__ = "insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_id: Mapped[str] = mapped_column(String(60), nullable=False)
    crew_id: Mapped[int] = mapped_column(Integer, ForeignKey("crew_members.id"), nullable=False)
    module: Mapped[str] = mapped_column(String(60), nullable=False)
    observation: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="monitor")  # monitor, warning, critical
    baseline_deviation_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    diagnosis: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default=None)  # strictly null
    requires_medical_review: Mapped[bool] = mapped_column(Boolean, default=False)
    metric_name: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    observed_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    baseline_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    z_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    crew_member: Mapped["CrewMember"] = relationship(back_populates="insights")


# ── ActionTaskRecord ─────────────────────────────────────────────────────

class ActionTaskRecord(Base):
    """Pre-approved action recommendations and crew task acknowledgments."""
    __tablename__ = "action_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action_id: Mapped[str] = mapped_column(String(80), nullable=False)
    crew_id: Mapped[int] = mapped_column(Integer, ForeignKey("crew_members.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(80), default="preapproved_action_library")
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, acknowledged, completed
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    crew_member: Mapped["CrewMember"] = relationship(back_populates="action_tasks")


# ── MedicalReportRecord ──────────────────────────────────────────────────

class MedicalReportRecord(Base):
    """Medical encounter reports prepared for ground transmission and physician review."""
    __tablename__ = "medical_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    crew_id: Mapped[int] = mapped_column(Integer, ForeignKey("crew_members.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(60), default="general")
    status: Mapped[str] = mapped_column(String(30), default="queued_for_sync")  # draft, queued_for_sync, transmitted, reviewed
    requires_physician_review: Mapped[bool] = mapped_column(Boolean, default=True)
    physician_decision: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)  # approved, amended, pending
    physician_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    future_phase_updates_json: Mapped[str] = mapped_column(Text, default="{}")
    checksum: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    crew_member: Mapped["CrewMember"] = relationship(back_populates="medical_reports")


# ── HealthCheckupRecord ──────────────────────────────────────────────────

class HealthCheckupRecord(Base):
    """Auditable session record for routine or specialized astronaut health checkups."""
    __tablename__ = "health_checkups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    checkup_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    astronaut_id: Mapped[str] = mapped_column(String(60), nullable=False)
    crew_id: Mapped[int] = mapped_column(Integer, ForeignKey("crew_members.id"), nullable=False)
    submitted_by_crew_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crew_members.id"), nullable=True)
    submitted_by_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    is_submitted_by_officer: Mapped[bool] = mapped_column(Boolean, default=False)
    checkup_date: Mapped[str] = mapped_column(String(30), nullable=False)  # YYYY-MM-DD
    checkup_time: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # HH:MM
    location: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    medical_officer: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    checkup_type: Mapped[str] = mapped_column(String(80), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submission_status: Mapped[str] = mapped_column(String(30), default="submitted")  # submitted, amended, synced
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True)
    is_amendment: Mapped[bool] = mapped_column(Boolean, default=False)
    amends_checkup_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    crew_member: Mapped["CrewMember"] = relationship(
        foreign_keys=[crew_id],
        back_populates="checkups"
    )
    submitted_by: Mapped[Optional["CrewMember"]] = relationship(
        foreign_keys=[submitted_by_crew_id]
    )
    measurements: Mapped[list["CheckupMeasurementRecord"]] = relationship(
        back_populates="checkup",
        cascade="all, delete-orphan"
    )
    files: Mapped[list["MedicalFileRecord"]] = relationship(
        back_populates="checkup",
        cascade="all, delete-orphan"
    )


# ── CheckupMeasurementRecord ─────────────────────────────────────────────

class CheckupMeasurementRecord(Base):
    """Discrete physiological or biochemical measurement captured during a checkup."""
    __tablename__ = "checkup_measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    checkup_id: Mapped[int] = mapped_column(Integer, ForeignKey("health_checkups.id"), nullable=False)
    domain: Mapped[str] = mapped_column(String(60), nullable=False)  # cardiovascular, immune, metabolic, radiation, sleep, neuromuscular, sans, basic
    metric_name: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    reference_range: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    data_source: Mapped[str] = mapped_column(String(40), default="manual_entry")  # manual_entry, report_upload, ocr_extracted
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    checkup: Mapped["HealthCheckupRecord"] = relationship(back_populates="measurements")


# ── MedicalFileRecord ────────────────────────────────────────────────────

class MedicalFileRecord(Base):
    """Uploaded clinical report or instrument artifact associated with a checkup."""
    __tablename__ = "medical_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    checkup_id: Mapped[int] = mapped_column(Integer, ForeignKey("health_checkups.id"), nullable=False)
    astronaut_id: Mapped[str] = mapped_column(String(60), nullable=False)
    health_module: Mapped[str] = mapped_column(String(60), default="general")
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/octet-stream")
    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    extracted_data_json: Mapped[str] = mapped_column(Text, default="{}")
    processing_status: Mapped[str] = mapped_column(String(40), default="stored")  # stored, parsing, verified, error
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    checkup: Mapped["HealthCheckupRecord"] = relationship(back_populates="files")
