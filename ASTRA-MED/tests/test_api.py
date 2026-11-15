"""API Route unit and integration tests (direct route execution for zero-latency)."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from astra_med.api.deps import (
    get_action_card_registry,
    get_alert_engine,
    get_baseline_engine,
    get_insight_engine,
    get_ml_router,
    get_store_forward_queue,
)
from astra_med.api.main import system_status
from astra_med.api.routes.action_cards import get_action_card, list_action_cards
from astra_med.api.routes.alerts import acknowledge_alert, get_alert_stats, list_active_alerts, list_alerts
from astra_med.api.routes.baselines import freeze_baseline, get_specific_baseline, list_baselines_for_crew, unfreeze_baseline
from astra_med.api.routes.biosample import (
    BloodPanelRequest,
    SalivaPanelRequest,
    UrinePanelRequest,
    ingest_blood_panel,
    ingest_saliva_panel,
    ingest_urine_panel,
)
from astra_med.api.routes.crew import CrewCreateRequest, create_crew, get_crew, list_crew
from astra_med.api.routes.ground_review import get_ground_queue, get_queue_depth, sync_encounter
from astra_med.api.routes.ml_inference import (
    MLPredictRequest,
    check_all_modules_health,
    check_module_health,
    predict_module,
)
from astra_med.api.routes.vitals import VitalIngestRequest, get_crew_vitals, get_latest_crew_vitals, ingest_vital


def test_system_status():
    status = system_status()
    assert status["status"] == "nominal"
    assert status["mode"] == "autonomous_offline"
    assert status["comms_latency_minutes"] == 20.0


def test_crew_endpoints(test_session: Session):
    # Create crew
    req = CrewCreateRequest(name="Dr. Jessica Watson", role="Mission Medical Specialist")
    created = create_crew(req=req, session=test_session)
    assert created.id is not None
    assert created.name == "Dr. Jessica Watson"

    # List crew
    crew_list = list_crew(session=test_session)
    assert len(crew_list) >= 1
    assert any(c.name == "Dr. Jessica Watson" for c in crew_list)

    # Get single crew
    detail = get_crew(crew_id=created.id, session=test_session)
    assert detail.role == "Mission Medical Specialist"


def test_vitals_ingest_nominal_vs_alert(test_session: Session, sample_crew):
    baseline_engine = get_baseline_engine()
    alert_engine = get_alert_engine()
    card_reg = get_action_card_registry()
    sf_queue = get_store_forward_queue()

    # 1. Ingest 10 nominal readings to satisfy BASELINE_MIN_SAMPLES = 10
    for i in range(10):
        req = VitalIngestRequest(
            crew_id=sample_crew.id,
            metric_name="heart_rate",
            value=72.0 + (i % 2),
            unit="bpm",
            timestamp_met=10.0 + i * 0.1,
        )
        res = ingest_vital(
            req=req,
            session=test_session,
            baseline_engine=baseline_engine,
            alert_engine=alert_engine,
            card_registry=card_reg,
            sf_queue=sf_queue,
        )
        assert res.alert_triggered is False

    # 2. Ingest extreme deviation (z > 3.5 sigma)
    extreme_req = VitalIngestRequest(
        crew_id=sample_crew.id,
        metric_name="heart_rate",
        value=175.0,
        unit="bpm",
        timestamp_met=15.0,
    )
    alert_res = ingest_vital(
        req=extreme_req,
        session=test_session,
        baseline_engine=baseline_engine,
        alert_engine=alert_engine,
        card_registry=card_reg,
        sf_queue=sf_queue,
    )
    assert alert_res.alert_triggered is True
    assert alert_res.severity in ("AMBER", "RED")
    assert alert_res.alert_id is not None


def test_alerts_acknowledge(test_session: Session, sample_crew):
    baseline_engine = get_baseline_engine()
    alert_engine = get_alert_engine()
    card_reg = get_action_card_registry()
    sf_queue = get_store_forward_queue()

    # Establish baseline with 10 readings
    for i in range(10):
        ingest_vital(
            req=VitalIngestRequest(
                crew_id=sample_crew.id,
                metric_name="bp_sys",
                value=120.0 + (i % 2),
                unit="mmHg",
                timestamp_met=float(i),
            ),
            session=test_session,
            baseline_engine=baseline_engine,
            alert_engine=alert_engine,
            card_registry=card_reg,
            sf_queue=sf_queue,
        )

    # Trigger alert with acute hypotension
    ingest_vital(
        req=VitalIngestRequest(
            crew_id=sample_crew.id,
            metric_name="bp_sys",
            value=80.0,
            unit="mmHg",
            timestamp_met=11.0,
        ),
        session=test_session,
        baseline_engine=baseline_engine,
        alert_engine=alert_engine,
        card_registry=card_reg,
        sf_queue=sf_queue,
    )

    active_alerts = list_active_alerts(crew_id=sample_crew.id, session=test_session)
    assert len(active_alerts) >= 1

    alert_id = active_alerts[0].id
    acked = acknowledge_alert(alert_id=alert_id, session=test_session)
    assert acked.acknowledged is True


def test_action_cards():
    reg = get_action_card_registry()
    cards = list_action_cards(hazard=None, severity=None, card_registry=reg)
    assert len(cards) >= 6

    card = get_action_card(card_id="CARD-CVD-AMBER-01", card_registry=reg)
    assert card.card_id == "CARD-CVD-AMBER-01"
    assert len(card.crew_instructions) > 0


def test_baselines_freeze_unfreeze(test_session: Session, sample_crew):
    baseline_engine = get_baseline_engine()
    alert_engine = get_alert_engine()
    card_reg = get_action_card_registry()
    sf_queue = get_store_forward_queue()

    # Establish baseline
    ingest_vital(
        req=VitalIngestRequest(
            crew_id=sample_crew.id,
            metric_name="temp_celsius",
            value=36.6,
            unit="C",
            timestamp_met=1.0,
        ),
        session=test_session,
        baseline_engine=baseline_engine,
        alert_engine=alert_engine,
        card_registry=card_reg,
        sf_queue=sf_queue,
    )

    # Freeze
    freeze_res = freeze_baseline(
        crew_id=sample_crew.id,
        metric_name="temp_celsius",
        session=test_session,
        baseline_engine=baseline_engine,
    )
    assert freeze_res["status"] == "frozen"

    # Unfreeze
    unfreeze_res = unfreeze_baseline(
        crew_id=sample_crew.id,
        metric_name="temp_celsius",
        session=test_session,
        baseline_engine=baseline_engine,
    )
    assert unfreeze_res["status"] == "unfrozen"


def test_biosample_ingestion(test_session: Session, sample_crew):
    baseline_engine = get_baseline_engine()
    alert_engine = get_alert_engine()
    card_reg = get_action_card_registry()
    sf_queue = get_store_forward_queue()

    # Blood panel
    blood_res = ingest_blood_panel(
        req=BloodPanelRequest(
            crew_id=sample_crew.id,
            timestamp_met=12.0,
            wbc_count_k_ul=7.1,
            neutrophil_pct=60.5,
            lymphocyte_pct=31.0,
            platelets_k_ul=230,
            il6_pg_ml=2.0,
            tnf_alpha_pg_ml=3.4,
        ),
        session=test_session,
        baseline_engine=baseline_engine,
        alert_engine=alert_engine,
        card_registry=card_reg,
        sf_queue=sf_queue,
    )
    assert blood_res["processed_analytes"] == 6

    # Urine panel
    urine_res = ingest_urine_panel(
        req=UrinePanelRequest(
            crew_id=sample_crew.id,
            timestamp_met=12.5,
            specific_gravity=1.018,
            ph=6.4,
            creatinine_mg_dl=115.0,
        ),
        session=test_session,
        baseline_engine=baseline_engine,
        alert_engine=alert_engine,
        card_registry=card_reg,
        sf_queue=sf_queue,
    )
    assert urine_res["processed_analytes"] == 3

    # Saliva panel
    saliva_res = ingest_saliva_panel(
        req=SalivaPanelRequest(
            crew_id=sample_crew.id,
            timestamp_met=13.0,
            cortisol_ug_dl=0.42,
            ebv_dna_copies_ml=0.0,
        ),
        session=test_session,
        baseline_engine=baseline_engine,
        alert_engine=alert_engine,
        card_registry=card_reg,
        sf_queue=sf_queue,
    )
    assert saliva_res["processed_analytes"] == 2


def test_ml_endpoints(test_session: Session, sample_crew):
    ml_router = get_ml_router()
    insight_engine = get_insight_engine()

    # Health check (all 7 modules: cardio, immune, metabolic, radiation, sleep, neuromuscular, sans)
    health_list = check_all_modules_health(ml_router=ml_router)
    assert len(health_list) == 7

    # Predict
    predict_res = predict_module(
        module_name="cardiovascular",
        req=MLPredictRequest(
            crew_id=sample_crew.id,
            input_data={
                "bp_systolic": 120,
                "bp_diastolic": 78,
                "hr": 74,
                "ecg_features": {"qrs_duration_ms": 90, "qt_interval_ms": 390},
            },
        ),
        session=test_session,
        ml_router=ml_router,
        insight_engine=insight_engine,
    )
    assert predict_res.module_name == "cardiovascular"
    assert predict_res.risk_label is not None
    assert predict_res.observation is not None
