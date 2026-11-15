"""ASTRA-MED Application Configuration.

All settings are offline-safe defaults. No cloud or external service dependency.
"""

from __future__ import annotations

import os
from pathlib import Path


# ── Paths ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # SpaceHealthX/
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "astra_med.db"
ACTION_CARDS_DIR = BASE_DIR / "action_cards"
FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"
TEMPLATES_DIR = FRONTEND_DIR / "templates"

# ── Database ──────────────────────────────────────────────────────────
DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("POSTGRES_URL")
    or f"sqlite:///{DB_PATH}"
)
UPLOADS_DIR = DATA_DIR / "uploads"
MEDICAL_FILES_DIR = UPLOADS_DIR / "medical_reports"
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB
ALLOWED_FILE_EXTENSIONS = {
    "pdf", "jpg", "jpeg", "png", "tiff", "tif", "dcm", "dicom",
    "csv", "json", "npy", "npz", "wav", "mp4", "webm"
}

# ── Auth / JWT ────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("ASTRA_SECRET_KEY", "astra-med-dev-secret-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 720  # 12 hours (long mission shifts)

# ── Baseline Engine ──────────────────────────────────────────────────
BASELINE_WINDOW_DAYS = 14          # rolling nominal window
BASELINE_MIN_SAMPLES = 10         # minimum samples before baseline is active
AMBER_THRESHOLD_SIGMA = 2.0       # ±2σ triggers AMBER
RED_THRESHOLD_SIGMA = 3.5         # ±3.5σ triggers RED

# ── Store-and-Forward ────────────────────────────────────────────────
COMMS_DELAY_MINUTES = 20          # nominal Mars one-way light delay
MAX_ENCOUNTER_QUEUE_SIZE = 10_000

# ── ML Module Config ─────────────────────────────────────────────────
ML_MODULES = [
    "cardiovascular",
    "immune",
    "metabolic",
    "radiation",
    "sleep",
    "neuromuscular",
    "sans",
]

# ── API ──────────────────────────────────────────────────────────────
API_V1_PREFIX = "/api/v1"
PROJECT_NAME = "ASTRA-MED"
PROJECT_VERSION = "0.1.0"
PROJECT_DESCRIPTION = "Autonomous Deep-Space Health & Acclimatization System"
