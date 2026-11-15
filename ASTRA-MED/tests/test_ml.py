"""Tests for Machine Learning Predictor Interfaces and Placeholder Implementations."""

from __future__ import annotations

import pytest

from astra_med.ml.interface import MLPredictor
from astra_med.ml.router import MLRouter


def test_ml_router_initialization():
    router = MLRouter()
    expected = ["cardiovascular", "immune", "metabolic", "radiation", "sleep", "neuromuscular", "sans"]
    assert set(expected).issubset(set(router.module_names))

    health = router.health_check_all()
    assert len(health) == 7
    for h in health:
        assert h["status"] in ("placeholder", "live")
        assert "version" in h


def test_cardiovascular_predictor():
    router = MLRouter()
    # Nominal input
    nominal_res = router.predict("cardiovascular", {
        "bp_systolic": 118, "bp_diastolic": 76, "hr": 70,
        "ecg_features": {"qrs_duration_ms": 90, "qt_interval_ms": 380}
    })
    assert "risk_label" in nominal_res
    assert "confidence" in nominal_res
    assert "risk_score" in nominal_res
    assert "details" in nominal_res
    assert 0.0 <= nominal_res["confidence"] <= 1.0

    # High-risk input
    high_risk_res = router.predict("cardiovascular", {
        "bp_systolic": 180, "bp_diastolic": 110, "hr": 150,
        "ecg_features": {"qrs_duration_ms": 140, "qt_interval_ms": 480}
    })
    assert high_risk_res["risk_score"] > nominal_res["risk_score"]


def test_immune_predictor():
    router = MLRouter()
    res = router.predict("immune", {
        "wbc_count": 6.2, "lymphocyte_pct": 30.0, "neutrophil_pct": 60.0,
        "il6": 1.5, "tnf_alpha": 3.0
    })
    assert "risk_label" in res
    assert res["confidence"] > 0.5


def test_metabolic_predictor():
    router = MLRouter()
    res = router.predict("metabolic", {
        "glucose": 90, "bun": 12, "creatinine": 0.85,
        "sodium": 140, "potassium": 4.0, "calcium": 9.4
    })
    assert "risk_label" in res
    assert "details" in res


def test_radiation_predictor():
    router = MLRouter()
    res = router.predict("radiation", {
        "cumulative_dose_msv": 120.0, "dose_rate": 1.2, "gamma_h2ax": 1.0
    })
    assert "risk_label" in res
    assert res["risk_score"] >= 0.0


def test_neuromuscular_predictor():
    router = MLRouter()
    res = router.predict("neuromuscular", {
        "gait_symmetry": 0.98, "stride_length": 0.75, "sway_velocity": 1.5, "reaction_time_ms": 230
    })
    assert "risk_label" in res


def test_sans_predictor():
    router = MLRouter()
    res = router.predict("sans", {
        "optic_disc_diameter": 4.9, "rnfl_thickness": 98, "iop": 14.5, "choroidal_folds": False
    })
    assert "risk_label" in res


def test_sleep_predictor():
    router = MLRouter()
    # Nominal sleep
    nominal = router.predict("sleep", {
        "sleep_duration_hours": 7.8,
        "rem_pct": 22.0,
        "deep_sleep_pct": 18.0,
        "awakenings": 1,
        "circadian_phase_shift_h": 0.2,
        "pvt_lapses": 0,
    })
    assert nominal["severity"] == "GREEN"
    assert nominal["confidence"] > 0.8

    # Disturbed sleep / sleep debt
    disturbed = router.predict("sleep", {
        "sleep_duration_hours": 4.5,
        "rem_pct": 10.0,
        "deep_sleep_pct": 8.0,
        "awakenings": 5,
        "circadian_phase_shift_h": 2.5,
        "pvt_lapses": 4,
    })
    assert disturbed["severity"] == "AMBER"
    assert disturbed["risk_score"] > nominal["risk_score"]


def test_ml_hot_swap():
    """Verify that placeholder can be replaced by real model without restart."""
    router = MLRouter()

    class CustomLivePredictor(MLPredictor):
        module_name = "cardiovascular"
        version = "1.0.0-trained-ptbxl"

        def predict(self, input_data: dict) -> dict:
            return {
                "risk_label": "Live-Tested Normal",
                "confidence": 0.99,
                "risk_score": 0.05,
                "details": {"model": "Trained PTB-XL ResNet1D"},
            }

        def health_check(self) -> dict:
            return {
                "module": self.module_name,
                "status": "live",
                "version": self.version,
            }

    router.swap_module("cardiovascular", CustomLivePredictor())
    health = router.health_check("cardiovascular")
    assert health["status"] == "live"
    assert health["version"] == "1.0.0-trained-ptbxl"

    pred = router.predict("cardiovascular", {})
    assert pred["risk_label"] == "Live-Tested Normal"
    assert pred["details"]["model"] == "Trained PTB-XL ResNet1D"
