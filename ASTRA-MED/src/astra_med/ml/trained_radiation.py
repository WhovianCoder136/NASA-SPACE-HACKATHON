from pathlib import Path
import sys
import tempfile
import pandas as pd

from astra_med.ml.interface import MLPredictor

ML_PROJECT = Path(r"D:\NASA SPACE APPS CHALLENGE\ASTRA_MED")
sys.path.insert(0, str(ML_PROJECT / "src"))

from integration.radiation_predict import predict_radiation


class TrainedRadiationPredictor(MLPredictor):
    module_name = "radiation"
    version = "1.0.0-experimental"

    def predict(self, input_data: dict) -> dict:
        csv_path = input_data.get("csv_path")
        if not csv_path:
            raise ValueError("Radiation SVM requires a gene-expression CSV file.")

        result = predict_radiation(csv_path)
        sample = result["results"][0]

        return {
            "risk_label": "EXPERIMENTAL_DOSE_PREDICTION",
            "confidence": max(sample["probabilities"].values()),
            "risk_score": 0.0,
            "details": {
                "predicted_dose_gy": sample["predicted_dose_gy"],
                "probabilities": sample["probabilities"],
                "timepoint_hours": sample["timepoint_hours"],
                "model": sample["model"],
                "experimental": True,
                "review_required": True,
                "astronaut_validation": False,
                "warning": sample["warning"],
                "sample_count": result["sample_count"]
            }
        }

    def health_check(self) -> dict:
        return {
            "module": self.module_name,
            "status": "live",
            "version": self.version,
            "description": "Experimental 48-hour gene-expression Linear SVM"
        }
