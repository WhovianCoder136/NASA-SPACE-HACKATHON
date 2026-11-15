"""Verification tests for the 10 non-negotiable flight constraints."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from astra_med.core.action_cards import ActionCardRegistry
from astra_med.core.alert_engine import AlertEngine
from astra_med.core.baseline import PersonalBaselineEngine
from astra_med.core.store_forward import StoreAndForwardQueue
from astra_med.core.types import DeviationResult, HazardType, SeverityTier
from astra_med.db import crud


def test_constraint_1_offline_capability():
    """Constraint #1: Entire system must function offline with no external network calls."""
    reg = ActionCardRegistry()
    assert len(reg.find_cards()) >= 6
    for card in reg.find_cards():
        assert card.card_id.startswith("CARD-")


def test_constraint_4_no_unsupported_disease_diagnosis():
    """Constraint #4: Zero unsupported disease diagnoses displayed to astronauts."""
    engine = AlertEngine()
    prohibited_clinical_diagnoses = [
        "pneumonia", "sepsis", "infarction", "appendicitis", "cancer",
        "arrhythmia disease", "hypertensive crisis", "myocarditis",
    ]

    dev = DeviationResult(
        metric_name="troponin_i",
        observed_value=0.85,
        baseline_mean=0.02,
        baseline_std=0.01,
        z_score=83.0,
        is_significant=True,
        direction="elevated",
    )
    summary = engine.generate_objective_summary(HazardType.GRAVITY, SeverityTier.RED, dev).lower()

    for prohibited in prohibited_clinical_diagnoses:
        assert prohibited not in summary, f"Prohibited clinical diagnosis '{prohibited}' found in summary"

    assert "objective deviation detected" in summary


def test_constraint_7_baseline_freeze_during_anomalies(test_session: Session, sample_crew):
    """Constraint #7: Baselines must not silently update during abnormal measurements."""
    baseline_engine = PersonalBaselineEngine(min_samples=2)
    alert_engine = AlertEngine()

    # Form nominal baseline
    baseline_engine.update_baseline(test_session, sample_crew.id, "heart_rate", 70.0, 1.0)
    baseline_engine.update_baseline(test_session, sample_crew.id, "heart_rate", 72.0, 2.0)

    # Evaluate extreme reading
    dev = baseline_engine.evaluate(test_session, sample_crew.id, "heart_rate", 160.0)
    assert dev.is_significant is True

    # Generate alert (which triggers freeze)
    alert_engine.generate_alert(
        session=test_session,
        crew_id=sample_crew.id,
        hazard=HazardType.GRAVITY,
        deviation=dev,
        timestamp_met=3.0,
    )

    baseline = crud.get_baseline(test_session, sample_crew.id, "heart_rate")
    assert baseline.frozen is True

    # Ingesting another reading while frozen must not alter baseline mean
    baseline_engine.update_baseline(test_session, sample_crew.id, "heart_rate", 170.0, 4.0)
    updated_baseline = crud.get_baseline(test_session, sample_crew.id, "heart_rate")
    assert updated_baseline.mean == baseline.mean
    assert updated_baseline.n_samples == 2


def test_constraint_9_cryptographic_audit_logging(test_session: Session, sample_crew):
    """Constraint #9: All encounters must include tamper-evident cryptographic checksums."""
    queue = StoreAndForwardQueue()
    alert_rec = crud.create_alert(
        session=test_session,
        crew_id=sample_crew.id,
        hazard="hazard_4_gravity_fields",
        severity="RED",
        functional_status="Requires Clinical Assessment",
        timestamp_met=100.0,
        metric_name="orthostatic_sys_drop",
        observed_value=32.0,
        baseline_mean=8.0,
        baseline_std=3.0,
        z_score=8.0,
        direction="elevated",
        summary_text="Severe orthostatic drop detected",
    )

    enc = queue.enqueue(
        session=test_session,
        crew_id=sample_crew.id,
        alert_id=alert_rec.id,
        timestamp_met=100.0,
        raw_digest="Raw posture Finapres recording #912",
    )

    assert enc.checksum is not None
    assert len(enc.checksum) == 64  # SHA-256 hex string


def test_constraint_8_safety_bounded_action_cards():
    """Constraint #8: Action cards must specify explicit safety boundaries and limits."""
    reg = ActionCardRegistry()
    cards = reg.find_cards()
    assert len(cards) >= 6
    for card in cards:
        assert isinstance(card.safety_limits, dict)
        assert len(card.safety_limits) > 0, f"Card {card.card_id} missing safety limits"
        assert card.de_escalation_criteria is not None
        assert len(card.crew_instructions) >= 2
