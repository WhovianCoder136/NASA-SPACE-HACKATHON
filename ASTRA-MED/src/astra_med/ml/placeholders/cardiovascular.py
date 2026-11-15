"""Cardiovascular placeholder predictor."""

from __future__ import annotations

from astra_med.ml.interface import MLPredictor


class CardiovascularPredictor(MLPredictor):
    module_name = "cardiovascular"
    version = "0.1.0-placeholder"

    def predict(self, input_data: dict) -> dict:
        bp_sys = input_data.get("bp_systolic", 120.0)
        bp_dia = input_data.get("bp_diastolic", 80.0)
        hr = input_data.get("hr", 72.0)
        ecg = input_data.get("ecg_features", {})

        risk_score = 0.0
        findings: list[str] = []

        # Blood pressure assessment
        if bp_sys > 180 or bp_dia > 120:
            risk_score += 0.4
            findings.append("Hypertensive crisis range")
        elif bp_sys > 140 or bp_dia > 90:
            risk_score += 0.25
            findings.append("Stage-2 hypertension")
        elif bp_sys > 130 or bp_dia > 85:
            risk_score += 0.1
            findings.append("Elevated blood pressure")

        # Heart rate assessment
        if hr > 120:
            risk_score += 0.25
            findings.append("Tachycardia detected")
        elif hr > 100:
            risk_score += 0.1
            findings.append("Mildly elevated heart rate")
        elif hr < 50:
            risk_score += 0.15
            findings.append("Bradycardia detected")

        # ECG features (simplified)
        if ecg.get("qt_interval_ms", 400) > 500:
            risk_score += 0.2
            findings.append("Prolonged QT interval")
        if ecg.get("st_deviation", 0.0) > 2.0:
            risk_score += 0.3
            findings.append("Significant ST deviation")

        risk_score = min(risk_score, 1.0)

        if risk_score >= 0.6:
            risk_label = "HIGH"
        elif risk_score >= 0.3:
            risk_label = "MODERATE"
        else:
            risk_label = "LOW"

        return {
            "risk_label": risk_label,
            "confidence": 0.75,
            "risk_score": round(risk_score, 3),
            "details": {
                "findings": findings if findings else ["Cardiovascular parameters nominal"],
                "bp_category": self._bp_category(bp_sys, bp_dia),
                "hr_category": self._hr_category(hr),
            },
        }

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _bp_category(sys: float, dia: float) -> str:
        if sys > 180 or dia > 120:
            return "crisis"
        if sys > 140 or dia > 90:
            return "stage2_hypertension"
        if sys > 130 or dia > 85:
            return "elevated"
        if sys < 90 or dia < 60:
            return "hypotension"
        return "normal"

    @staticmethod
    def _hr_category(hr: float) -> str:
        if hr > 120:
            return "tachycardia"
        if hr > 100:
            return "elevated"
        if hr < 50:
            return "bradycardia"
        return "normal"
