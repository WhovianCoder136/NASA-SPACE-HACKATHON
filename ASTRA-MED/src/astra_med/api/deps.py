"""FastAPI dependency injection and singleton providers."""

from __future__ import annotations

from astra_med.core.action_cards import ActionCardRegistry
from astra_med.core.action_engine import ActionEngine
from astra_med.core.alert_engine import AlertEngine
from astra_med.core.baseline import PersonalBaselineEngine
from astra_med.core.insight_engine import InsightEngine
from astra_med.core.store_forward import StoreAndForwardQueue
from astra_med.db.database import get_db
from astra_med.ml.router import MLRouter

# Application singletons (stateful in memory, backed by SQLite)
_ml_router = MLRouter()
_baseline_engine = PersonalBaselineEngine()
_alert_engine = AlertEngine()
_action_card_registry = ActionCardRegistry()
_store_forward_queue = StoreAndForwardQueue()
_insight_engine = InsightEngine()
_action_engine = ActionEngine()


def get_ml_router() -> MLRouter:
    return _ml_router


def get_baseline_engine() -> PersonalBaselineEngine:
    return _baseline_engine


def get_alert_engine() -> AlertEngine:
    return _alert_engine


def get_action_card_registry() -> ActionCardRegistry:
    return _action_card_registry


def get_store_forward_queue() -> StoreAndForwardQueue:
    return _store_forward_queue


def get_insight_engine() -> InsightEngine:
    return _insight_engine


def get_action_engine() -> ActionEngine:
    return _action_engine
