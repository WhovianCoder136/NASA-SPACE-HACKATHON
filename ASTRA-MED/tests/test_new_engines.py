"""Tests for Insight Engine, Action Engine, Medical Reports, and Unified Endpoints."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from astra_med.api.deps import (
    get_action_card_registry,
    get_action_engine,
    get_alert_engine,
    get_baseline_engine,
    get_insight_engine,
    get_store_forward_queue,
)
from astra_med.api.routes.actions import (
    AcknowledgeRequest,
    AssignActionRequest,
    acknowledge_action,
    assign_action_task,
    list_actions_and_tasks,
)
from astra_med.api.routes.astronauts import get_astronaut_overview, list_astronauts
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
from astra_med.core.types import DeviationResult


def test_insight_engine_strictly_no_diagnosis(test_session: Session, sample_crew):
    engine = get_insight_engine()

    # 1. Nominal deviation
    nominal_dev = DeviationResult(
        metric_name="heart_rate",
        observed_value=72.0,
        baseline_mean=70.0,
        baseline_std=4.0,
        z_score=0.5,
        is_significant=False,
        direction="nominal",
    )
    rec1 = engine.evaluate_deviation(test_session, sample_crew.id, "cardiovascular", nominal_dev)
    assert rec1.diagnosis is None
    assert rec1.severity == "monitor"
    assert "within the subject's established flight baseline" in rec1.observation

    # 2. Significant deviation
    elevated_dev = DeviationResult(
        metric_name="glucose",
        observed_value=145.0,
        baseline_mean=90.0,
        baseline_std=10.0,
        z_score=5.5,
        is_significant=True,
        direction="elevated",
    )
    rec2 = engine.evaluate_deviation(test_session, sample_crew.id, "metabolic", elevated_dev)
    assert rec2.diagnosis is None  # strictly null
    assert rec2.severity == "critical"
    assert rec2.requires_medical_review is True
    assert "Significant physiological deviation" in rec2.observation


def test_action_engine_preapproved_actions(test_session: Session, sample_crew):
    action_engine = get_action_engine()
    lib = action_engine.get_library()
    assert len(lib) >= 6

    # Verify hydration reminder exists
    hyd = action_engine.get_action_by_id("ACT-HYD-01")
    assert hyd is not None
    assert "Electrolyte" in hyd["title"]

    # Dispatch action task
    task = action_engine.dispatch_action(test_session, sample_crew.id, "ACT-HYD-01")
    assert task.status == "pending"

    # Acknowledge task
    ack = action_engine.acknowledge_action(test_session, "ACT-HYD-01", notes="Hydration completed.")
    assert ack.status == "acknowledged"
    assert ack.acknowledged_at is not None


def test_medical_reports_workflow(test_session: Session, sample_crew):
    # 1. Create medical report
    req = CreateMedicalReportRequest(
        crew_id=sample_crew.id,
        title="Post-EVA Orthostatic Evaluation",
        summary="Subject completed 6-hour EVA. Observed minor transient postural blood pressure drop.",
        domain="cardiovascular",
        requires_physician_review=True,
        future_phase_updates={"next_eva_rest_interval_hours": 36},
    )
    created = create_medical_report(req=req, session=test_session)
    assert created.status == "queued_for_sync"
    assert created.checksum != ""
    assert created.requires_physician_review is True

    # 2. Simulate Earth sync
    synced = sync_report(report_id=created.report_id, session=test_session)
    assert synced.status == "transmitted"
    assert synced.synced_at is not None

    # 3. Simulate Flight Surgeon Review
    rev_req = ReviewReportRequest(
        physician_name="Dr. Mercer, MD",
        decision="approved",
        comments="Approved. Continue hydration protocol and monitor 24h vitals.",
        future_phase_updates={"phase_4_adaptation_tier": "optimal"},
    )
    reviewed = review_report(report_id=created.report_id, req=rev_req, session=test_session)
    assert reviewed.status == "reviewed"
    assert reviewed.physician_decision == "approved"
    assert "Dr. Mercer" in reviewed.physician_comments
    assert reviewed.future_phase_updates.get("phase_4_adaptation_tier") == "optimal"


def test_unified_measurements_and_astronaut_overview(test_session: Session, sample_crew):
    # Ingest measurement via unified endpoint
    req = MeasurementIngestRequest(
        astronaut_id=f"ASTRA-{sample_crew.id:03d}",
        crew_id=sample_crew.id,
        domain="sleep",
        metric_name="sleep_duration_hours",
        value=7.4,
        unit="hours",
        timestamp_met=142.1,
    )
    m_res = ingest_measurement(
        req=req,
        session=test_session,
        baseline_engine=get_baseline_engine(),
        alert_engine=get_alert_engine(),
        insight_engine=get_insight_engine(),
        card_registry=get_action_card_registry(),
        sf_queue=get_store_forward_queue(),
    )
    assert m_res.metric_name == "sleep_duration_hours"
    assert m_res.observation is not None

    # Retrieve astronaut overview
    overview = get_astronaut_overview(str(sample_crew.id), session=test_session)
    assert overview.name == sample_crew.name
    assert overview.astronaut_id == f"ASTRA-{sample_crew.id:03d}"
    assert len(overview.latest_vitals) >= 1
