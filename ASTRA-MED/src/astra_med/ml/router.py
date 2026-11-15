
"""Dispatch JSON demo predictions and trained file-based model inference."""

from __future__ import annotations

from typing import Dict

from astra_med.ml.interface import MLPredictor
from astra_med.ml.placeholders.cardiovascular import CardiovascularPredictor
from astra_med.ml.placeholders.immune import ImmunePredictor
from astra_med.ml.placeholders.metabolic import MetabolicPredictor
from astra_med.ml.placeholders.neuromuscular import NeuromuscularPredictor
from astra_med.ml.placeholders.sans import SANSPredictor
from astra_med.ml.placeholders.sleep import SleepPredictor
from astra_med.ml.trained_adapters import predict_file, file_model_health


class RadiationDemoPredictor(MLPredictor):
    module_name = "radiation"
    version = "demo-upload-required"

    def predict(self, input_data: dict) -> dict:
        return {
            "risk_label": "UPLOAD_REQUIRED",
            "risk_score": 0.0,
            "confidence": 0.0,
            "details": {
                "message": "Upload the 48-hour gene-expression CSV to run the trained radiation model.",
                "demo_input_received": list(input_data.keys()),
                "experimental_model": True,
                "astronaut_validation": False,
            },
        }

    def health_check(self):
        return {
            "module": self.module_name,
            "status": "upload_required",
            "version": self.version,
        }


class MLRouter:
    def __init__(self) -> None:
        self._modules: Dict[str, MLPredictor] = {
            "cardiovascular": CardiovascularPredictor(),
            "immune": ImmunePredictor(),
            "metabolic": MetabolicPredictor(),
            "radiation": RadiationDemoPredictor(),
            "sleep": SleepPredictor(),
            "neuromuscular": NeuromuscularPredictor(),
            "sans": SANSPredictor(),
        }

    def predict(self, module_name: str, input_data: dict) -> dict:
        predictor = self._modules.get(module_name)
        if predictor is None:
            raise KeyError(f"Unknown ML module: {module_name}")

        if module_name in ("immune", "metabolic") and {
            "subject_id", "measurements"
        }.issubset(input_data):
            from astra_med.ml.trained_adapters import _module, _result
            module = _module(f"{module_name}_predict")
            fn = getattr(module, f"predict_{module_name}")
            output = fn(
                input_data["subject_id"],
                input_data["measurements"],
                timepoint=input_data.get("timepoint"),
            )
            return _result(
                "BASELINE_DEVIATION_ANALYSIS",
                {
                    "subject_id": input_data["subject_id"],
                    "analysis_type": "subject_baseline_deviation",
                    "result": output,
                    "interpretation": "Baseline deviation analysis, not a disease probability.",
                },
            )

        return predictor.predict(input_data)

    def predict_file(self, module_name: str, path, metadata=None) -> dict:
        if module_name not in self._modules:
            raise KeyError(f"Unknown ML module: {module_name}")
        return predict_file(module_name, path, metadata)

    def health_check_all(self) -> list[dict]:
        legacy = [p.health_check() for p in self._modules.values()]
        trained = file_model_health()
        trained_by_name = {x["module"]: x for x in trained}
        for item in legacy:
            name = item.get("module")
            if name in trained_by_name:
                item["trained_file_inference"] = trained_by_name[name]
        return legacy

    def health_check(self, module_name: str) -> dict:
        predictor = self._modules.get(module_name)
        if predictor is None:
            raise KeyError(f"Unknown ML module: {module_name}")
        result = predictor.health_check()
        result["trained_file_inference"] = {
            "module": module_name,
            "status": "registered",
            "inference_mode": "file_upload",
        }
        return result

    def swap_module(self, module_name: str, new_predictor: MLPredictor) -> None:
        if module_name not in self._modules:
            raise KeyError(f"Unknown ML module: {module_name}")
        self._modules[module_name] = new_predictor

    @property
    def module_names(self) -> list[str]:
        return list(self._modules.keys())
