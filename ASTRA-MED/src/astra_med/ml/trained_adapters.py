
from __future__ import annotations

import importlib
import json
import os
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import joblib

MODEL_ROOT = Path(os.getenv(
    "ASTRA_MED_MODEL_ROOT",
    r"D:\NASA SPACE APPS CHALLENGE\ASTRA_MED"
)).resolve()

INTEGRATION_ROOT = MODEL_ROOT / "src"
if str(INTEGRATION_ROOT) not in sys.path:
    sys.path.insert(0, str(INTEGRATION_ROOT))


def _module(name):
    return importlib.import_module(f"integration.{name}")


def _clean(value):
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")
    if isinstance(value, pd.Series):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    return value


def _result(label, details, score=0.0, confidence=0.0):
    return {
        "risk_label": label,
        "risk_score": float(score),
        "confidence": float(confidence),
        "details": _clean(details),
    }


@lru_cache(maxsize=1)
def _cardiovascular_model():
    module = _module("cardiovascular_predict")
    return module.CardiovascularPredictor()


def predict_cardiovascular(path, metadata):
    frame = pd.read_csv(path, header=None)
    values = frame.apply(pd.to_numeric, errors="raise").to_numpy(dtype=float)
    sampling_rate = int(metadata.get("sampling_rate", 100))
    output = _cardiovascular_model().predict_array(values, sampling_rate)
    return _result(
        "ECG_MODEL_PREDICTION",
        output,
        confidence=0.0,
    )


def _subject_measurements(path, metadata):
    frame = pd.read_csv(path)
    if frame.empty:
        raise ValueError("The uploaded CSV contains no measurements.")
    subject = metadata.get("subject_id")
    if not subject:
        raise ValueError("Provide subject_id (C001, C002, C003 or C004).")
    row = frame.iloc[0].dropna().to_dict()
    row.pop("subject_id", None)
    row.pop("timepoint", None)
    return subject, row


def predict_immune(path, metadata):
    subject, measurements = _subject_measurements(path, metadata)
    module = _module("immune_predict")
    output = module.predict_immune(
        subject,
        measurements,
        metadata.get("timepoint"),
    )
    return _result(
        "BASELINE_DEVIATION_ANALYSIS",
        {
            "analysis_type": "subject_baseline_deviation",
            "subject_id": subject,
            "interpretation": "This is deviation from the supplied baseline profile, not a disease probability.",
            "result": output,
        },
    )


def predict_metabolic(path, metadata):
    subject, measurements = _subject_measurements(path, metadata)
    module = _module("metabolic_predict")
    output = module.predict_metabolic(
        subject,
        measurements,
        timepoint=metadata.get("timepoint"),
    )
    return _result(
        "BASELINE_DEVIATION_ANALYSIS",
        {
            "analysis_type": "subject_baseline_deviation",
            "subject_id": subject,
            "interpretation": "This is deviation from the supplied baseline profile, not a disease probability.",
            "result": output,
        },
    )


def predict_radiation(path, metadata):
    module = _module("radiation_predict")
    output = module.predict_radiation(str(path))
    samples = output.get("results", [])
    if not samples:
        raise ValueError("Radiation model returned no predictions.")
    first = samples[0]
    return _result(
        "EXPERIMENTAL_DOSE_PREDICTION",
        {
            "predicted_dose_gy": first.get("predicted_dose_gy"),
            "probabilities": first.get("probabilities"),
            "timepoint_hours": first.get("timepoint_hours", 48),
            "model": first.get("model"),
            "experimental": True,
            "review_required": True,
            "astronaut_validation": False,
            "warning": first.get("warning"),
            "sample_count": output.get("sample_count", len(samples)),
            "all_results": samples,
        },
    )


@lru_cache(maxsize=1)
def _sleep_bundle():
    module = _module("sleep_predict")
    model, metadata, features, classes = module.load_model()
    return module, model, metadata, features, classes


def predict_sleep(path, metadata):
    module, model, model_metadata, features, classes = _sleep_bundle()
    frame = module.load_feature_csv(str(path), features)
    prepared = module.prepare_input(frame, features)
    predictions = module.predict_stages(model, prepared, classes)

    if isinstance(predictions, pd.DataFrame):
        records = predictions.to_dict(orient="records")
        stage_column = predictions.get("predicted_stage")
        stages = stage_column.tolist() if stage_column is not None else []
        confidence_column = predictions.get("prediction_confidence")
        confidences = confidence_column.tolist() if confidence_column is not None else []
    else:
        records = _clean(predictions)
        stages = []
        confidences = []

    architecture = None
    if stages:
        try:
            architecture = module.calculate_architecture(stages)
        except Exception as exc:
            architecture = {"summary_error": str(exc)}

    return _result(
        "SLEEP_STAGE_PREDICTION",
        {
            "model": "TabPFN sleep-stage classifier",
            "predictions": records,
            "sleep_architecture": _clean(architecture),
            "epoch_count": len(stages),
            "mean_prediction_confidence": (
                float(np.nanmean(confidences)) if confidences else None
            ),
        },
        confidence=float(np.nanmean(confidences)) if confidences else 0.0,
    )


@lru_cache(maxsize=1)
def _sans_bundle():
    module = _module("sans_predict")
    loaded = module.load_model()
    model = loaded[0] if isinstance(loaded, tuple) else loaded
    return module, model


def predict_sans(path, metadata):
    module, model = _sans_bundle()
    output = module.predict(str(path), model)
    details = _clean(output)

    if isinstance(details, dict):
        for key in list(details):
            value = details[key]
            if isinstance(value, list) and len(value) > 2000:
                details[key] = {
                    "omitted_from_response": True,
                    "element_count": len(value),
                }

    return _result(
        "SANS_IMAGE_SEGMENTATION",
        {
            "task": "optic-disc/retinal image segmentation",
            "interpretation": "Segmentation output; not a standalone clinical diagnosis.",
            "output": details,
        },
    )


@lru_cache(maxsize=2)
def _gait_model(model_type):
    model_dir = MODEL_ROOT / "models" / "neuromuscular"
    names = {
        "emg": "emg_gait_speed_classifier.joblib",
        "multimodal": "multimodal_gait_speed_classifier.joblib",
    }
    if model_type not in names:
        raise ValueError("model_type must be 'emg' or 'multimodal'.")
    path = model_dir / names[model_type]
    if not path.exists():
        raise FileNotFoundError(f"Neuromuscular model not found: {path}")
    return joblib.load(path)


def predict_neuromuscular(path, metadata):
    frame = pd.read_csv(path)
    model_type = metadata.get("model_type", "emg").lower()
    model = _gait_model(model_type)
    expected = list(getattr(model, "feature_names_in_", []))
    if not expected:
        raise ValueError("The gait model does not expose feature_names_in_.")
    missing = [name for name in expected if name not in frame.columns]
    if missing:
        raise ValueError(
            f"{model_type} gait CSV is missing {len(missing)} required columns. "
            f"First missing columns: {missing[:12]}"
        )
    x = frame[expected].apply(pd.to_numeric, errors="raise")
    prediction = model.predict(x)
    probabilities = model.predict_proba(x) if hasattr(model, "predict_proba") else None
    return _result(
        "GAIT_SPEED_CLASSIFICATION",
        {
            "model_type": model_type,
            "predicted_gait_speed_classes": prediction.tolist(),
            "class_probabilities": probabilities.tolist() if probabilities is not None else None,
            "sample_count": len(frame),
            "feature_count": len(expected),
            "classes": _clean(getattr(model, "classes_", [])),
            "astronaut_validation": False,
        },
        confidence=float(np.max(probabilities[0])) if probabilities is not None else 0.0,
    )


PREDICTORS = {
    "cardiovascular": predict_cardiovascular,
    "immune": predict_immune,
    "metabolic": predict_metabolic,
    "radiation": predict_radiation,
    "sleep": predict_sleep,
    "neuromuscular": predict_neuromuscular,
    "sans": predict_sans,
}


def predict_file(module_name, path, metadata=None):
    if module_name not in PREDICTORS:
        raise KeyError(f"Unknown ML module: {module_name}")
    return PREDICTORS[module_name](Path(path), metadata or {})


def file_model_health():
    result = []
    for name in PREDICTORS:
        result.append({
            "module": name,
            "status": "registered",
            "inference_mode": "file_upload",
            "model_root": str(MODEL_ROOT),
        })
    return result
