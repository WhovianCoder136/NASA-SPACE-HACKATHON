"""ASTRA-MED Action Engine.

Maintains a comprehensive library of flight-surgeon pre-approved, non-diagnostic
support actions, countermeasures, and workflow tasks. Handles crew assignment,
acknowledgment, and tracking.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from astra_med.db import crud
from astra_med.db.models import ActionTaskRecord


# Pre-approved operational library
PREAPPROVED_ACTIONS: List[Dict[str, Any]] = [
    {
        "action_id": "ACT-HYD-01",
        "title": "Electrolyte & Fluid Volume Loading",
        "description": "Ingest 500 mL water with oral electrolyte rehydration sachet over 30 minutes to support circulating plasma volume.",
        "source": "preapproved_action_library",
        "approval_required": False,
        "hazard": "hazard_4_gravity_fields",
    },
    {
        "action_id": "ACT-PST-02",
        "title": "Staged Postural Orthostatic Transition",
        "description": "Remain seated with bilateral calf flexions for 3 minutes before executing upright standing maneuver during microgravity-to-hypergravity transition.",
        "source": "preapproved_action_library",
        "approval_required": False,
        "hazard": "hazard_4_gravity_fields",
    },
    {
        "action_id": "ACT-SLP-03",
        "title": "Circadian Reset & Dynamic Blue Light Notch",
        "description": "Activate 460nm notch cabin lighting filter 2 hours prior to sleep window. Perform 10-minute paced diaphragmatic breathing protocol.",
        "source": "preapproved_action_library",
        "approval_required": False,
        "hazard": "hazard_2_isolation_and_confinement",
    },
    {
        "action_id": "ACT-RPT-04",
        "title": "Repeat Telemetry Verification Cycle",
        "description": "Conduct repeat vital measurement (continuous BP cuff and 3-lead ECG) in 15 minutes to confirm trajectory of observed deviation.",
        "source": "preapproved_action_library",
        "approval_required": False,
        "hazard": "general",
    },
    {
        "action_id": "ACT-EXR-05",
        "title": "Countermeasure Resistive Ergometer Adjustment",
        "description": "Maintain daily cycle ergometer / ARED resistive loading at 75% VO2max for 45 minutes; adjust harness load to 80% body mass equivalent.",
        "source": "preapproved_action_library",
        "approval_required": False,
        "hazard": "hazard_4_gravity_fields",
    },
    {
        "action_id": "ACT-REP-06",
        "title": "Compile Ground Telemedicine Encounter Dossier",
        "description": "Bundle recent telemetry, baseline deviation statistics, and action card execution record into store-and-forward package for Earth review.",
        "source": "preapproved_action_library",
        "approval_required": False,
        "hazard": "hazard_3_distance_from_earth",
    },
]


class ActionEngine:
    """Orchestrates pre-approved operational actions and task acknowledgments."""

    def __init__(self, action_library: Optional[List[Dict[str, Any]]] = None):
        self.library = action_library or PREAPPROVED_ACTIONS

    def get_library(self) -> List[Dict[str, Any]]:
        return self.library

    def get_action_by_id(self, action_id: str) -> Optional[Dict[str, Any]]:
        for act in self.library:
            if act["action_id"] == action_id:
                return act
        return None

    def recommend_for_module(self, module: str, severity: str = "monitor") -> List[Dict[str, Any]]:
        """Find appropriate pre-approved actions based on affected health module."""
        mod = module.lower()
        recs = []
        if "cardio" in mod or "gravity" in mod:
            recs.extend([self.get_action_by_id("ACT-HYD-01"), self.get_action_by_id("ACT-PST-02")])
        elif "sleep" in mod or "isolation" in mod:
            recs.append(self.get_action_by_id("ACT-SLP-03"))
        elif "metabolic" in mod:
            recs.append(self.get_action_by_id("ACT-HYD-01"))
        
        # In all cases of warning or critical, recommend repeat verification and ground report
        if severity in ("warning", "critical"):
            recs.append(self.get_action_by_id("ACT-RPT-04"))
            recs.append(self.get_action_by_id("ACT-REP-06"))

        return [r for r in recs if r is not None]

    def dispatch_action(
        self,
        session: Session,
        crew_id: int,
        action_id: str,
        notes: Optional[str] = None,
    ) -> ActionTaskRecord:
        """Instantiate an action as an active task for an astronaut."""
        template = self.get_action_by_id(action_id)
        if not template:
            # Fallback custom or card id
            return crud.create_action_task(
                session=session,
                action_id=action_id,
                crew_id=crew_id,
                title=f"Protocol Action: {action_id}",
                description=f"Execute pre-approved flight protocol {action_id}.",
                source="action_card",
                notes=notes,
            )

        return crud.create_action_task(
            session=session,
            action_id=template["action_id"],
            crew_id=crew_id,
            title=template["title"],
            description=template["description"],
            source=template.get("source", "preapproved_action_library"),
            approval_required=template.get("approval_required", False),
            notes=notes,
        )

    def acknowledge_action(
        self,
        session: Session,
        action_id: str,
        notes: Optional[str] = None,
    ) -> Optional[ActionTaskRecord]:
        """Acknowledge action execution."""
        return crud.acknowledge_action_task(session, action_id, notes=notes)
