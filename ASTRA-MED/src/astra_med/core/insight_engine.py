"""ASTRA-MED Insight Engine.

Converts multi-domain physiological telemetry, baseline deviations, and ML module outputs
into clear, actionable, non-diagnostic observational insights for astronauts and delayed flight surgeons.

SAFETY INVARIANT:
This engine NEVER autonomously diagnoses disease, prescribes medication, or alters medical protocols.
The field `diagnosis` is strictly `null`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from astra_med.core.types import DeviationResult, SeverityTier
from astra_med.db import crud
from astra_med.db.models import InsightRecord


class InsightEngine:
    """Transforms raw analytics and baseline evaluations into human-readable observations."""

    def generate_observation_text(
        self,
        module: str,
        metric_name: str,
        observed_value: float,
        baseline_mean: float,
        baseline_std: float,
        z_score: float,
        direction: str,
    ) -> str:
        """Formulate plain-language, non-alarmist observational summary."""
        sign = "+" if z_score > 0 else ""
        delta_pct = ((observed_value - baseline_mean) / baseline_mean * 100) if baseline_mean != 0 else 0

        readable_module = module.replace("_", " ").capitalize()
        readable_metric = metric_name.replace("_", " ").title()

        if abs(z_score) < 2.0:
            return (
                f"{readable_module} metric {readable_metric} is currently within the subject's established "
                f"flight baseline ({observed_value:.1f} vs nominal {baseline_mean:.1f} ± {baseline_std:.1f})."
            )

        dir_word = "above" if z_score > 0 else "below"
        shift_desc = f"{abs(delta_pct):.1f}% {dir_word}" if baseline_mean != 0 else f"{dir_word}"

        if abs(z_score) >= 3.5:
            return (
                f"Significant physiological deviation: {readable_metric} ({observed_value:.1f}) is {shift_desc} "
                f"the subject's personal flight baseline ({baseline_mean:.1f} ± {baseline_std:.1f}, z={sign}{z_score:.2f}). "
                f"Pre-approved operational stabilization guidance triggered; ground medical review recommended."
            )
        else:
            return (
                f"{readable_metric} is {shift_desc} the subject's recorded flight baseline "
                f"({observed_value:.1f} vs {baseline_mean:.1f} ± {baseline_std:.1f}, z={sign}{z_score:.2f}). "
                f"Routine countermeasure protocol suggested."
            )

    def evaluate_deviation(
        self,
        session: Session,
        crew_id: int,
        module: str,
        deviation: DeviationResult,
        subject_id: Optional[str] = None,
    ) -> InsightRecord:
        """Create structured Insight from a personal baseline DeviationResult."""
        sid = subject_id or f"ASTRA-{crew_id:03d}"
        abs_z = abs(deviation.z_score)

        if abs_z >= 3.5:
            severity = "critical"
            requires_review = True
        elif abs_z >= 2.0:
            severity = "warning"
            requires_review = False
        else:
            severity = "monitor"
            requires_review = False

        observation = self.generate_observation_text(
            module=module,
            metric_name=deviation.metric_name,
            observed_value=deviation.observed_value,
            baseline_mean=deviation.baseline_mean,
            baseline_std=deviation.baseline_std,
            z_score=deviation.z_score,
            direction=deviation.direction,
        )

        return crud.create_insight(
            session=session,
            subject_id=sid,
            crew_id=crew_id,
            module=module,
            observation=observation,
            severity=severity,
            baseline_deviation_detected=deviation.is_significant,
            diagnosis=None,  # strictly null
            requires_medical_review=requires_review,
            metric_name=deviation.metric_name,
            observed_value=deviation.observed_value,
            baseline_mean=deviation.baseline_mean,
            z_score=deviation.z_score,
        )

    def evaluate_ml_prediction(
        self,
        session: Session,
        crew_id: int,
        module: str,
        prediction: Dict[str, Any],
        subject_id: Optional[str] = None,
    ) -> InsightRecord:
        """Create structured Insight from ML model prediction output."""
        sid = subject_id or f"ASTRA-{crew_id:03d}"
        risk_label = prediction.get("risk_label", "Evaluated")
        risk_score = float(prediction.get("risk_score", 0.0))
        details = prediction.get("details", {})

        if risk_score >= 0.70:
            severity = "critical"
            requires_review = True
        elif risk_score >= 0.40:
            severity = "warning"
            requires_review = False
        else:
            severity = "monitor"
            requires_review = False

        # Craft human-readable insight
        flags = details.get("detected_flags", [])
        flags_text = f" Noted patterns: {'; '.join(flags)}." if flags else ""

        observation = (
            f"{module.capitalize()} ML evaluation indicates '{risk_label}' "
            f"(computed composite index: {risk_score * 100:.1f}/100, confidence: {prediction.get('confidence', 0.85)*100:.0f}%)."
            f"{flags_text}"
        )

        return crud.create_insight(
            session=session,
            subject_id=sid,
            crew_id=crew_id,
            module=module,
            observation=observation,
            severity=severity,
            baseline_deviation_detected=(risk_score >= 0.40),
            diagnosis=None,  # strictly null
            requires_medical_review=requires_review,
            observed_value=risk_score,
        )
