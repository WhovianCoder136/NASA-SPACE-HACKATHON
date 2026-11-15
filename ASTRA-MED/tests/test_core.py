"""Unit tests for ASTRA-MED Core Monitoring and Clinical Decision Engines."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from astra_med.core.alert_engine import AlertEngine
from astra_med.core.baseline import PersonalBaselineEngine
from astra_med.core.store_forward import StoreAndForwardQueue
from astra_med.core.types import DeviationResult, FunctionalStatus, HazardType, SeverityTier
from astra_med.db import crud


def test_baseline_welford_calculation(test_session: Session, sample_crew):
    engine = PersonalBaselineEngine(amber_threshold=2.0, min_samples=3)
    values = [70.0, 72.0, 74.0, 70.0, 72.0]

    for val in values:
        engine.update_baseline(
            session=test_session,
            crew_id=sample_crew.id,
            metric_name="heart_rate",
            new_value=val,
            timestamp_met=1.0,
        )

    baseline = crud.get_baseline(test_session, sample_crew.id, "heart_rate")
    assert baseline is not None
    assert baseline.n_samples == 5
    assert abs(baseline.mean - 71.6) < 0.1
    assert baseline.std > 0.5


def test_baseline_freeze_prevents_update(test_session: Session, sample_crew):
    """Constraint #7: Baselines must never silently update during abnormal measurements."""
    engine = PersonalBaselineEngine(amber_threshold=2.0, min_samples=3)

    # Establish baseline
    for val in [120.0, 120.0, 120.0]:
        engine.update_baseline(test_session, sample_crew.id, "bp_sys", val, 1.0)

    # Freeze baseline (as happens during an alert)
    engine.freeze(test_session, sample_crew.id, "bp_sys")

    # Ingest abnormal measurement
    engine.update_baseline(test_session, sample_crew.id, "bp_sys", 180.0, 2.0)

    # Verify baseline mean remains unchanged
    baseline = crud.get_baseline(test_session, sample_crew.id, "bp_sys")
    assert baseline.mean == 120.0
    assert baseline.n_samples == 3
    assert baseline.frozen is True


def test_baseline_unfreeze_allows_update(test_session: Session, sample_crew):
    engine = PersonalBaselineEngine()
    engine.update_baseline(test_session, sample_crew.id, "spo2", 98.0, 1.0)
    engine.freeze(test_session, sample_crew.id, "spo2")
    engine.unfreeze(test_session, sample_crew.id, "spo2")

    engine.update_baseline(test_session, sample_crew.id, "spo2", 99.0, 2.0)
    baseline = crud.get_baseline(test_session, sample_crew.id, "spo2")
    assert baseline.n_samples == 2
    assert baseline.frozen is False


def test_alert_engine_severity_tiers():
    alert_engine = AlertEngine(amber_sigma=2.0, red_sigma=3.5)

    green_dev = DeviationResult(
        metric_name="hr", observed_value=72, baseline_mean=70, baseline_std=2.0,
        z_score=1.0, is_significant=False, direction="nominal"
    )
    assert alert_engine.classify_severity(green_dev) == SeverityTier.GREEN

    amber_dev = DeviationResult(
        metric_name="hr", observed_value=75, baseline_mean=70, baseline_std=2.0,
        z_score=2.5, is_significant=True, direction="elevated"
    )
    assert alert_engine.classify_severity(amber_dev) == SeverityTier.AMBER

    red_dev = DeviationResult(
        metric_name="hr", observed_value=85, baseline_mean=70, baseline_std=2.0,
        z_score=4.0, is_significant=True, direction="elevated"
    )
    assert alert_engine.classify_severity(red_dev) == SeverityTier.RED


def test_no_unsupported_disease_diagnosis_in_alert_summary():
    """Constraint #4: The system outputs objective physiological deviations, never disease diagnoses."""
    alert_engine = AlertEngine()
    dev = DeviationResult(
        metric_name="leukocytes", observed_value=14.0, baseline_mean=6.5, baseline_std=1.2,
        z_score=6.25, is_significant=True, direction="elevated"
    )
    summary = alert_engine.generate_objective_summary(HazardType.IMMUNE, SeverityTier.RED, dev)

    unsupported_diagnoses = ["pneumonia", "leukemia", "infection", "sepsis", "myocarditis", "hypertension"]
    for word in unsupported_diagnoses:
        assert word not in summary.lower()

    assert "Objective Deviation Detected" in summary
    assert "leukocytes" in summary


def test_store_and_forward_enqueue_and_checksum(test_session: Session, sample_crew):
    """Hazard 3: Autonomous delayed store-and-forward queue with cryptographic checksums."""
    queue = StoreAndForwardQueue()

    alert_rec = crud.create_alert(
        session=test_session,
        crew_id=sample_crew.id,
        hazard="hazard_4_gravity_fields",
        severity="AMBER",
        functional_status="Incomplete Adaptation",
        timestamp_met=14.5,
        metric_name="bp_systolic",
        observed_value=88.0,
        baseline_mean=118.0,
        baseline_std=5.0,
        z_score=-6.0,
        direction="depressed",
        summary_text="Orthostatic systolic BP drop",
        action_card_id="CARD-CVD-AMBER-01",
    )

    encounter = queue.enqueue(
        session=test_session,
        crew_id=sample_crew.id,
        alert_id=alert_rec.id,
        timestamp_met=14.5,
        action_card_id="CARD-CVD-AMBER-01",
        raw_digest="Systolic drop of 30 mmHg observed",
    )

    assert encounter.encounter_uuid.startswith("enc-")
    assert len(encounter.checksum) == 64  # SHA-256 hex length
    assert encounter.ground_synced is False

    depth = queue.get_queue_depth(test_session)
    assert depth == 1

    # Simulate downlink
    queue.mark_synced(test_session, encounter.id)
    depth_after = queue.get_queue_depth(test_session)
    assert depth_after == 0
