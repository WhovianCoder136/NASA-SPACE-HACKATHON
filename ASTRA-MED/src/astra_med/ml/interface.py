"""ML Predictor abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod


class MLPredictor(ABC):
    """Abstract base class for all ML predictors (placeholder and live)."""

    module_name: str = ""
    version: str = "0.1.0"

    @abstractmethod
    def predict(self, input_data: dict) -> dict:
        """Run prediction on *input_data*.

        Returns
        -------
        dict with keys:
            risk_label  – human-readable risk label (str)
            confidence  – 0.0 … 1.0 (float)
            details     – arbitrary detail dict
            risk_score  – 0.0 … 1.0 (float)
        """

    def health_check(self) -> dict:
        """Return module health information."""
        return {
            "module": self.module_name,
            "status": "placeholder",
            "version": self.version,
        }
