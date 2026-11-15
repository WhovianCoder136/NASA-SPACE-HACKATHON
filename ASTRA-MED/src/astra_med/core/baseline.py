"""Personal Baseline Engine using Welford's algorithm and anomaly-freezing safeguards."""

from __future__ import annotations

import math
from typing import Optional
from sqlalchemy.orm import Session

from astra_med.config import AMBER_THRESHOLD_SIGMA, BASELINE_MIN_SAMPLES
from astra_med.core.types import DeviationResult
from astra_med.db import crud
from astra_med.db.models import PersonalBaselineRecord


class PersonalBaselineEngine:
    """Manages individual astronaut baselines with strict anomaly protection."""

    def __init__(self, amber_threshold: float = AMBER_THRESHOLD_SIGMA, min_samples: int = BASELINE_MIN_SAMPLES):
        self.amber_threshold = amber_threshold
        self.min_samples = min_samples

    def get_or_create_baseline(
        self, session: Session, crew_id: int, metric_name: str
    ) -> PersonalBaselineRecord:
        record = crud.get_baseline(session, crew_id, metric_name)
        if record is None:
            record = crud.upsert_baseline(
                session=session,
                crew_id=crew_id,
                metric_name=metric_name,
                mean=0.0,
                std=1.0,
                n_samples=0,
                frozen=False,
                last_updated_met=0.0,
            )
        return record

    def update_baseline(
        self,
        session: Session,
        crew_id: int,
        metric_name: str,
        new_value: float,
        timestamp_met: float,
        force: bool = False,
    ) -> Optional[PersonalBaselineRecord]:
        """Update personal baseline using Welford's online variance algorithm.
        
        Strict safety invariant: Skips update if baseline is frozen (active anomaly)
        unless force=True.
        """
        record = self.get_or_create_baseline(session, crew_id, metric_name)
        if record.frozen and not force:
            return record

        n = record.n_samples
        old_mean = record.mean
        old_std = record.std

        if n == 0:
            new_mean = float(new_value)
            new_std = 1.0  # initial default variance unit
            new_n = 1
        elif n == 1:
            new_n = 2
            new_mean = (old_mean + new_value) / 2.0
            diff = abs(new_value - old_mean)
            new_std = max(diff / math.sqrt(2), 0.001)
        else:
            # Welford update
            new_n = n + 1
            delta = new_value - old_mean
            new_mean = old_mean + delta / new_n
            delta2 = new_value - new_mean
            m2_old = (old_std ** 2) * (n - 1)
            m2_new = m2_old + delta * delta2
            variance = m2_new / (new_n - 1)
            new_std = max(math.sqrt(max(variance, 0.0)), 0.001)

        updated = crud.upsert_baseline(
            session=session,
            crew_id=crew_id,
            metric_name=metric_name,
            mean=new_mean,
            std=new_std,
            n_samples=new_n,
            frozen=record.frozen,
            last_updated_met=timestamp_met,
        )
        return updated

    def evaluate(
        self,
        session: Session,
        crew_id: int,
        metric_name: str,
        value: float,
    ) -> DeviationResult:
        """Evaluate observed metric value against astronaut's personal baseline."""
        record = crud.get_baseline(session, crew_id, metric_name)
        if record is None or record.n_samples < self.min_samples:
            mean = record.mean if record else value
            std = record.std if record and record.std > 0 else 1.0
            z_score = 0.0
            return DeviationResult(
                metric_name=metric_name,
                observed_value=value,
                baseline_mean=mean,
                baseline_std=std,
                z_score=z_score,
                is_significant=False,
                direction="nominal",
            )

        mean = record.mean
        std = max(record.std, 0.001)
        z_score = (value - mean) / std

        is_significant = abs(z_score) >= self.amber_threshold
        if z_score > self.amber_threshold:
            direction = "elevated"
        elif z_score < -self.amber_threshold:
            direction = "depressed"
        else:
            direction = "nominal"

        return DeviationResult(
            metric_name=metric_name,
            observed_value=value,
            baseline_mean=mean,
            baseline_std=std,
            z_score=round(z_score, 3),
            is_significant=is_significant,
            direction=direction,
        )

    def freeze(self, session: Session, crew_id: int, metric_name: str) -> bool:
        """Freeze baseline to prevent pollution during abnormal physiological states."""
        return crud.freeze_baseline(session, crew_id, metric_name)

    def unfreeze(self, session: Session, crew_id: int, metric_name: str) -> bool:
        """Unfreeze baseline once physiology has returned to verified nominal state."""
        return crud.unfreeze_baseline(session, crew_id, metric_name)

    def should_freeze(self, deviation: DeviationResult) -> bool:
        """Returns True if an observed deviation warrants immediate baseline freezing."""
        return deviation.is_significant
