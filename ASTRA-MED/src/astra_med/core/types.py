"""ASTRA-MED Core Domain Types.

Pydantic models and enums shared across the entire application.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────

class CrewStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class SeverityTier(str, enum.Enum):
    """Three-tier clinical alert classification."""
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"


class HazardType(str, enum.Enum):
    """NASA human spaceflight hazards and system components."""
    RADIATION = "hazard_1_space_radiation"
    ISOLATION = "hazard_2_isolation_and_confinement"
    DISTANCE = "hazard_3_distance_from_earth"
    GRAVITY = "hazard_4_gravity_fields"
    IMMUNE = "hazard_5_hostile_closed_environments"
    BIOSAMPLE = "biosample_intelligence_engine"


class GARPhase(str, enum.Enum):
    """Gravity Adaptation & Rehabilitation phases."""
    PRE_TRANSITION = "PRE_TRANSITION"
    TRANSITION = "TRANSITION"
    POST_TRANSITION = "POST_TRANSITION"


class FunctionalStatus(str, enum.Enum):
    """Objective functional adaptation and status ratings."""
    NOMINAL = "NOMINAL"
    OPTIMAL = "Optimal Functional State"
    PROGRESSING = "Adaptation Progressing"
    INCOMPLETE_ADAPTATION = "Incomplete Adaptation"
    REQUIRES_CLINICAL_ASSESSMENT = "Requires Clinical Assessment"
    DEGRADED = "DEGRADED"
    INCAPACITATED = "INCAPACITATED"
    CRITICAL = "CRITICAL"


class DeviationDirection(str, enum.Enum):
    HIGH = "HIGH"
    LOW = "LOW"
    NORMAL = "NORMAL"
    ELEVATED = "elevated"
    DEPRESSED = "depressed"
    NOMINAL = "nominal"


class SampleType(str, enum.Enum):
    CONTINUOUS = "continuous"
    SPOT = "spot"
    DERIVED = "derived"
    BLOOD = "blood"
    URINE = "urine"
    SALIVA = "saliva"


class DataPedigreeTier(str, enum.Enum):
    """Pedigree classification to strictly prevent invalid flight readiness claims."""
    TIER_1_FLIGHT = "Tier 1: Authentic Human Astronaut Flight Data"
    TIER_2_ANALOGUE = "Tier 2: Terrestrial Ground Analogue (Bed-Rest/HERA)"
    TIER_3_MODELED = "Tier 3: Modeled Microgravity (In-Vitro / Clinostat)"
    TIER_4_ANIMAL = "Tier 4: Pre-clinical Animal Spaceflight / Ground"
    TIER_5_TERRESTRIAL = "Tier 5: Terrestrial Clinical Cohort (PhysioNet)"


# ── Pydantic Models ─────────────────────────────────────────────────────

class QualityScore(BaseModel):
    is_valid: bool = Field(True, description="True if signal passes quality thresholds")
    sqi_score: float = Field(1.0, ge=0.0, le=1.0, description="Normalized signal quality index")
    flags: List[str] = Field(default_factory=list)


class BiomarkerMeasurement(BaseModel):
    metric_name: str
    value: float
    unit: str
    timestamp_met: float
    sample_type: Optional[str] = "continuous"
    quality: QualityScore = Field(default_factory=QualityScore)


class PersonalBaseline(BaseModel):
    subject_id: str
    metric_name: str
    mean: float
    std: float = Field(..., gt=0.0)
    n_samples: int = Field(..., ge=0)
    frozen: bool = False
    last_updated_met: float = 0.0


class DeviationResult(BaseModel):
    """Result of evaluating a value against a personal baseline."""
    metric_name: str
    observed_value: float
    baseline_mean: float
    baseline_std: float
    z_score: float
    direction: str = "nominal"
    is_significant: bool = False


class AlertEvent(BaseModel):
    """Event emitted when an alert is generated."""
    alert_id: Optional[str] = None
    alert_uuid: Optional[str] = None
    crew_id: Optional[int] = None
    subject_id: Optional[str] = None
    hazard: Union[HazardType, str]
    severity: SeverityTier
    functional_status: FunctionalStatus = FunctionalStatus.NOMINAL
    metric_name: Optional[str] = None
    observed_value: Optional[float] = None
    z_score: Optional[float] = None
    direction: Optional[str] = None
    deviation: Optional[DeviationResult] = None
    summary_text: str = ""
    action_card_id: Optional[str] = None
    timestamp_met: float = 0.0


class ActionCard(BaseModel):
    """Action card schema loaded from JSON files."""
    card_id: str
    version: str = "1.0"
    hazard: Union[HazardType, str]
    severity: SeverityTier
    title: str
    plain_language_summary: str
    crew_instructions: List[str] = Field(default_factory=list)
    safety_limits: Dict[str, Any] = Field(default_factory=dict)
    de_escalation_criteria: Optional[str] = ""


class VitalSubmission(BaseModel):
    """Incoming vital reading from a sensor or manual entry."""
    crew_id: int
    metric_name: str
    value: float
    unit: str
    timestamp_met: float
    sample_type: SampleType = SampleType.CONTINUOUS
    sqi_score: float = 1.0
    sqi_valid: bool = True
    flags: Dict[str, Any] = Field(default_factory=dict)


class EncounterPackage(BaseModel):
    """A bundled encounter ready for store-and-forward."""
    encounter_uuid: str
    crew_id: int
    timestamp_met: float
    alert_uuid: Optional[str] = None
    alert_id: Optional[int] = None
    action_card_id: Optional[str] = None
    raw_digest: str = ""
    checksum: str = ""


class MedicalEncounterPackage(BaseModel):
    encounter_id: str
    subject_id: str
    timestamp_met: float
    alert: AlertEvent
    action_card: Optional[ActionCard] = None
    raw_telemetry_digest: str = ""
    crew_acknowledged: bool = False
    ground_synced: bool = False
    checksum: str = ""


class GroundReview(BaseModel):
    """Review from ground control for an encounter."""
    encounter_id: int
    reviewer: str
    review_text: str
    recommendations: List[str] = Field(default_factory=list)
    approved_updates: Dict[str, Any] = Field(default_factory=dict)
    received_met: float = 0.0


class MLPrediction(BaseModel):
    """Prediction output from an ML module."""
    crew_id: int
    module_name: str
    input_summary: str = ""
    prediction: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    timestamp_met: float = 0.0
