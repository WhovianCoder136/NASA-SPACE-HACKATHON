"""ML Router – dispatches predictions to the appropriate module."""

from __future__ import annotations

from typing import Dict

from astra_med.ml.interface import MLPredictor
from astra_med.ml.placeholders.cardiovascular import CardiovascularPredictor
from astra_med.ml.placeholders.immune import ImmunePredictor
from astra_med.ml.placeholders.metabolic import MetabolicPredictor
from astra_med.ml.placeholders.radiation import RadiationPredictor
from astra_med.ml.placeholders.neuromuscular import NeuromuscularPredictor
from astra_med.ml.placeholders.sans import SANSPredictor
from astra_med.ml.placeholders.sleep import SleepPredictor


class MLRouter:
    """Routes prediction requests to the correct ML module."""

    def __init__(self) -> None:
        self._modules: Dict[str, MLPredictor] = {
            "cardiovascular": CardiovascularPredictor(),
            "immune": ImmunePredictor(),
            "metabolic": MetabolicPredictor(),
            "radiation": RadiationPredictor(),
            "sleep": SleepPredictor(),
            "neuromuscular": NeuromuscularPredictor(),
            "sans": SANSPredictor(),
        }

    def predict(self, module_name: str, input_data: dict) -> dict:
        """Route *input_data* to the named module and return its prediction."""
        predictor = self._modules.get(module_name)
        if predictor is None:
            raise KeyError(f"Unknown ML module: {module_name}")
        return predictor.predict(input_data)

    def health_check_all(self) -> list[dict]:
        """Return health status for every loaded module."""
        return [p.health_check() for p in self._modules.values()]

    def health_check(self, module_name: str) -> dict:
        """Return health status for a single module."""
        predictor = self._modules.get(module_name)
        if predictor is None:
            raise KeyError(f"Unknown ML module: {module_name}")
        return predictor.health_check()

    def swap_module(self, module_name: str, new_predictor: MLPredictor) -> None:
        """Hot-swap a placeholder with a real model."""
        if module_name not in self._modules:
            raise KeyError(f"Unknown ML module: {module_name}")
        self._modules[module_name] = new_predictor

    @property
    def module_names(self) -> list[str]:
        return list(self._modules.keys())
