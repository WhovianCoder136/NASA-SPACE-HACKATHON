"""Clinical Alert Engine implementing 3-tier severity without unsupported disease diagnosis."""

from __future__ import annotations

import uuid
from typing import Optional
from sqlalchemy.orm import Session

from astra_med.config import AMBER_THRESHOLD_SIGMA, RED_THRESHOLD_SIGMA
from astra_med.core.types import (
    AlertEvent,
    DeviationResult,
    FunctionalStatus,
    HazardType,
    SeverityTier,
)
from astra_med.db import crud
from astra_med.db.models import AlertRecord


class AlertEngine:
    """Classifies physiological deviations into clinical tiers and triggers safe countermeasures."""

    def __init__(
        self,
        amber_sigma: float = AMBER_THRESHOLD_SIGMA,
        red_sigma: float = RED_THRESHOLD_SIGMA,
    ):
        self.amber_sigma = amber_sigma
        self.red_sigma = red_sigma

    def classify_severity(self, deviation: DeviationResult) -> SeverityTier:
        """Classify deviation based on sigma thresholds."""
        abs_z = abs(deviation.z_score)
        if abs_z >= self.red_sigma:
            return SeverityTier.RED
        elif abs_z >= self.amber_sigma:
            return SeverityTier.AMBER
        return SeverityTier.GREEN

    def map_functional_status(
        self,
        hazard: HazardType,
        severity: SeverityTier,
        deviation: DeviationResult,
    ) -> FunctionalStatus:
        """Map hazard severity to objective functional status (Constraint #4: No disease diagnosis)."""
        if severity == SeverityTier.GREEN:
            return FunctionalStatus.OPTIMAL
        elif severity == SeverityTier.AMBER:
            if hazard == HazardType.GRAVITY:
                return FunctionalStatus.INCOMPLETE_ADAPTATION
            return FunctionalStatus.PROGRESSING
        else:  # RED
            return FunctionalStatus.REQUIRES_CLINICAL_ASSESSMENT

    def generate_objective_summary(
        self,
        hazard: HazardType,
        severity: SeverityTier,
        deviation: DeviationResult,
    ) -> str:
        """Generate objective summary text strictly free of unsupported disease labels."""
        direction_text = deviation.direction.upper()
        return (
            f"Objective Deviation Detected: {deviation.metric_name} is {direction_text} "
            f"(observed: {deviation.observed_value:.2f}, baseline: {deviation.baseline_mean:.2f} ± {deviation.baseline_std:.2f}, "
            f"z-score: {deviation.z_score:+.2f}). Severity tier: {severity.value}. "
            f"Advisory: Execute approved protocol."
        )

    def generate_alert(
        self,
        session: Session,
        crew_id: int,
        hazard: HazardType,
        deviation: DeviationResult,
        timestamp_met: float,
        action_card_id: Optional[str] = None,
    ) -> AlertEvent:
        """Create alert, enforce baseline protection, and return AlertEvent."""
        severity = self.classify_severity(deviation)
        status = self.map_functional_status(hazard, severity, deviation)
        summary = self.generate_objective_summary(hazard, severity, deviation)

        # Auto-freeze baseline during AMBER/RED deviations (Constraint #7)
        if severity in (SeverityTier.AMBER, SeverityTier.RED):
            crud.freeze_baseline(session, crew_id, deviation.metric_name)

        record = crud.create_alert(
            session=session,
            crew_id=crew_id,
            hazard=hazard.value,
            severity=severity.value,
            functional_status=status.value,
            timestamp_met=timestamp_met,
            metric_name=deviation.metric_name,
            observed_value=deviation.observed_value,
            baseline_mean=deviation.baseline_mean,
            baseline_std=deviation.baseline_std,
            z_score=deviation.z_score,
            direction=deviation.direction,
            summary_text=summary,
            action_card_id=action_card_id,
        )

        return AlertEvent(
            alert_id=record.alert_uuid,
            alert_uuid=record.alert_uuid,
            subject_id=str(crew_id),
            crew_id=crew_id,
            hazard=hazard,
            severity=severity,
            functional_status=status,
            timestamp_met=timestamp_met,
            deviation=deviation,
            summary_text=summary,
            action_card_id=action_card_id,
        )
