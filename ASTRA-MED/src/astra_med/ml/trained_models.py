from pathlib import Path
import os
import sys
import json
import joblib
import numpy as np
import pandas as pd

from astra_med.ml.interface import MLPredictor

MODEL_ROOT = Path(os.getenv(
    "ASTRA_MED_MODEL_ROOT",
    r"D:\NASA SPACE APPS CHALLENGE\ASTRA_MED"
))
INTEGRATION_ROOT = MODEL_ROOT / "src"

if not INTEGRATION_ROOT.exists():
    raise RuntimeError(f"Integration scripts not found: {INTEGRATION_ROOT}")

sys.path.insert(0, str(INTEGRATION_ROOT))

from integration.cardiovascular_predict import CardiovascularPredictor
from integration.immune_predict import ImmunePredictor
from integration.metabolic_predict import MetabolicPredictor
from integration.radiation_predict import predict_radiation
from integration.sans_predict import load_model as load_sans_model
from integration.sans_predict import predict as predict_sans
from integration.sleep_predict import load_model as load_sleep_model
from integration.sleep_predict import prepare_input, predict_stages
from integration.sleep_predict import calculate_architecture


def json_safe(value):
    return json.loads(json.dumps(value, default=lambda x:
        x.item() if isinstance(x, np.generic)
        else x.tolist() if isinstance(x, np.ndarray)
        else str(x)
    ))


def file_path(data):
    path = data.get("_file_path")
    if not path:
        raise ValueError("This model requires an uploaded input file.")
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError("Uploaded input file is unavailable.")
    return path


class LazyPredictor(MLPredictor):
    _instance = None

    def get_model(self):
        if self._instance is None:
            self._instance = self.load_model()
        return self._instance


class TrainedCardiovascularPredictor(LazyPredictor):
    module_name = "cardiovascular"
    version = "1.0.0-ptbxl-cnn"

    def load_model(self):
        return CardiovascularPredictor()

    def predict(self, input_data):
        path = file_path(input_data)
        sampling_rate = int(input_data.get("sampling_rate", 100))

        data = pd.read_csv(path)
        if data.shape != (1000, 12):
            raise ValueError(
                f"ECG CSV must contain 1000 rows and 12 lead columns. "
                f"Received {data.shape}."
            )

        signal = data.apply(pd.to_numeric, errors="coerce").to_numpy()
        if not np.isfinite(signal).all():
            raise ValueError("ECG CSV contains missing or non-numeric values.")

        result = self.get_model().predict_array(signal, sampling_rate)
        probabilities = result["predictions"]
        confidence = max(probabilities.values(), default=0.0)

        return {
            "risk_label": (
                "ECG_CATEGORIES_DETECTED"
                if result["detected_categories"]
                else "NO_CATEGORY_ABOVE_THRESHOLD"
            ),
            "confidence": float(confidence),
            "risk_score": float(confidence),
            "details": json_safe(result),
        }

    def health_check(self):
        return {
            "module": self.module_name,
            "status": "ready",
            "version": self.version,
            "input": "1000 x 12 ECG CSV",
            "clinical_validation": False,
        }


class TrainedImmunePredictor(LazyPredictor):
    module_name = "immune"
    version = "1.0.0-baseline-profile"

    def load_model(self):
        return ImmunePredictor()

    def predict(self, input_data):
        subject = input_data.get("subject_id")
        if not subject:
            raise ValueError("Provide subject_id (C001, C002, C003 or C004).")

        measurements = input_data.get("measurements")
        if not isinstance(measurements, dict):
            raise ValueError("Provide biomarker measurements as a dictionary.")

        result = self.get_model().predict(
            subject,
            measurements,
            input_data.get("timepoint"),
        )

        result = json_safe(result)
        flags = result.get("flags", [])
        confidence = 0.0

        return {
            "risk_label": "BASELINE_DEVIATION_ANALYSIS",
            "confidence": confidence,
            "risk_score": 0.0,
            "details": {
                "analysis_type": "subject_specific_baseline_deviation",
                "subject_id": subject,
                "result": result,
                "flag_count": len(flags) if isinstance(flags, list) else None,
                "is_disease_classifier": False,
            },
        }

    def health_check(self):
        return {
            "module": self.module_name,
            "status": "ready",
            "version": self.version,
            "model_type": "subject-specific biomarker baseline profile",
        }


class TrainedMetabolicPredictor(LazyPredictor):
    module_name = "metabolic"
    version = "1.0.0-baseline-profile"

    def load_model(self):
        return MetabolicPredictor()

    def predict(self, input_data):
        subject = input_data.get("subject_id")
        if not subject:
            raise ValueError("Provide a subject_id.")

        measurements = input_data.get("measurements")
        if not isinstance(measurements, dict):
            raise ValueError("Provide biochemical measurements as a dictionary.")

        result = self.get_model().predict(
            subject=subject,
            measurements=measurements,
            reference_ranges=input_data.get("reference_ranges"),
            timepoint=input_data.get("timepoint"),
        )

        result = json_safe(result)

        return {
            "risk_label": "METABOLIC_BASELINE_ANALYSIS",
            "confidence": 0.0,
            "risk_score": 0.0,
            "details": {
                "analysis_type": "subject-specific baseline and reference-range analysis",
                "subject_id": subject,
                "result": result,
                "is_disease_classifier": False,
            },
        }

    def health_check(self):
        return {
            "module": self.module_name,
            "status": "ready",
            "version": self.version,
            "model_type": "subject-specific biochemical baseline profile",
        }


class TrainedRadiationPredictor(MLPredictor):
    module_name = "radiation"
    version = "1.0.0-experimental"

    def predict(self, input_data):
        result = predict_radiation(file_path(input_data))
        samples = result.get("results", [])

        if not samples:
            raise ValueError("Radiation model returned no predictions.")

        sample = samples[0]
        probabilities = sample.get("probabilities", {})
        confidence = max(probabilities.values(), default=0.0)

        return {
            "risk_label": "EXPERIMENTAL_DOSE_PREDICTION",
            "confidence": float(confidence),
            "risk_score": 0.0,
            "details": {
                "results": json_safe(samples),
                "sample_count": result.get("sample_count", len(samples)),
                "experimental": True,
                "review_required": True,
                "astronaut_validation": False,
            },
        }

    def health_check(self):
        return {
            "module": self.module_name,
            "status": "ready",
            "version": self.version,
            "input": "gene-expression CSV with 17259 required features",
            "experimental": True,
            "astronaut_validation": False,
        }


class TrainedSANSPredictor(LazyPredictor):
    module_name = "sans"
    version = "1.0.0-unet"

    def load_model(self):
        return load_sans_model()

    def predict(self, input_data):
        path = file_path(input_data)
        result = predict_sans(
            path,
            self.get_model(),
            threshold=float(input_data.get("threshold", 0.5)),
        )

        result = json_safe(result)
        confidence = float(result.get("mean_probability", 0.0))

        return {
            "risk_label": "SANS_IMAGE_SEGMENTATION",
            "confidence": confidence,
            "risk_score": 0.0,
            "details": {
                "segmentation": result,
                "research_prototype": True,
                "clinical_validation": False,
            },
        }

    def health_check(self):
        return {
            "module": self.module_name,
            "status": "ready",
            "version": self.version,
            "input": "medical image",
            "clinical_validation": False,
        }


class TrainedSleepPredictor(LazyPredictor):
    module_name = "sleep"
    version = "1.0.0-tabpfn"

    def load_model(self):
        return load_sleep_model()

    def predict(self, input_data):
        path = file_path(input_data)
        model, metadata, features, classes = self.get_model()

        dataframe = pd.read_csv(path)
        if dataframe.empty:
            raise ValueError("Sleep feature CSV is empty.")

        missing = [f for f in features if f not in dataframe.columns]
        if missing:
            raise ValueError(
                f"Sleep CSV is missing {len(missing)} required features. "
                f"Examples: {missing[:10]}"
            )

        X = prepare_input(dataframe, features)
        output = predict_stages(model, X, classes)
        architecture = calculate_architecture(output["predicted_stage"])

        stage_counts = output["predicted_stage"].value_counts().to_dict()
        mean_confidence = float(output["prediction_confidence"].mean())

        return {
            "risk_label": "SLEEP_STAGE_ANALYSIS_COMPLETE",
            "confidence": mean_confidence,
            "risk_score": 0.0,
            "details": {
                "model": "TabPFN sleep-stage classifier",
                "epoch_count": len(output),
                "stage_counts": json_safe(stage_counts),
                "mean_prediction_confidence": mean_confidence,
                "architecture": json_safe(architecture),
                "astronaut_validation": False,
            },
        }

    def health_check(self):
        return {
            "module": self.module_name,
            "status": "ready",
            "version": self.version,
            "input": "CSV with 57 extracted sleep features",
        }


class TrainedNeuromuscularPredictor(MLPredictor):
    module_name = "neuromuscular"
    version = "1.0.0-gait-pipelines"

    def __init__(self):
        self._models = None

    def get_models(self):
        if self._models is None:
            directory = MODEL_ROOT / "models" / "neuromuscular"
            emg_path = directory / "emg_gait_speed_classifier.joblib"
            multimodal_path = directory / "multimodal_gait_speed_classifier.joblib"

            if not emg_path.exists() or not multimodal_path.exists():
                raise FileNotFoundError("Neuromuscular model artifacts are missing.")

            self._models = {
                "emg": joblib.load(emg_path),
                "multimodal": joblib.load(multimodal_path),
            }

        return self._models

    def predict(self, input_data):
        path = file_path(input_data)
        dataframe = pd.read_csv(path)

        if dataframe.empty:
            raise ValueError("Neuromuscular feature CSV is empty.")

        results = {}

        for name, model in self.get_models().items():
            features = list(model.feature_names_in_)
            missing = [f for f in features if f not in dataframe.columns]

            if missing:
                continue

            X = dataframe[features].apply(pd.to_numeric, errors="coerce")

            if not np.isfinite(X.to_numpy()).all():
                raise ValueError(f"{name} input contains missing or non-numeric features.")

            probabilities = model.predict_proba(X)
            predictions = model.predict(X)

            results[name] = {
                "predictions_m_per_second": predictions.tolist(),
                "classes": model.classes_.tolist(),
                "probabilities": probabilities.tolist(),
                "feature_count": len(features),
            }

        if not results:
            raise ValueError(
                "CSV does not contain the required 143 EMG or 287 multimodal features."
            )

        first = next(iter(results.values()))
        confidence = float(np.max(first["probabilities"][0]))

        return {
            "risk_label": "GAIT_SPEED_PREDICTION",
            "confidence": confidence,
            "risk_score": 0.0,
            "details": {
                "results": json_safe(results),
                "interpretation": "Predicted gait speed in metres per second; not a diagnosis.",
            },
        }

    def health_check(self):
        return {
            "module": self.module_name,
            "status": "ready",
            "version": self.version,
            "models": {
                "emg": "143 features",
                "multimodal": "287 features",
            },
        }
