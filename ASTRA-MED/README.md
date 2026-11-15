# ASTRA-MED
### Autonomous Deep-Space Health & Acclimatization System

ASTRA-MED is an autonomous, offline-first medical monitoring and clinical decision-support system designed for long-duration deep-space exploration (crewed 3-year Mars mission with 6–9 months transit each way and ~20-minute one-way light speed delay).

---

## 1. Project Architecture & Parallel Responsibilities

To maximize velocity and maintain clean separation of concerns, development is partitioned into two parallel workstreams:

```
┌────────────────────────────────────────────────────────┐
│                   ASTRA-MED PLATFORM                   │
├────────────────────────────┬───────────────────────────┤
│    USER / ML WORKSTREAM    │  FULL-STACK APP (BUILT)   │
│                            │                           │
│  1. Cardiovascular         │  FastAPI Async Backend    │
│     (PTB-XL ECG & Finapres)│  SQLite + aiosqlite (WAL) │
│  2. Immune System          │  Personal Baseline Engine │
│     (NASA OSD-575)         │  (Welford online stats)   │
│  3. Metabolic & Renal      │  Alert Engine             │
│     (OSD-575 CMP)          │  (GREEN / AMBER / RED)    │
│  4. Space Radiation        │  Action Card Registry     │
│     (NASA OSD-157)         │  (6 pre-approved cards)   │
│  5. Neuromuscular & Gait   │  Store-and-Forward Queue  │
│     (Multimodal Gait & CoP)│  (SHA-256 encounter pkgs) │
│  6. SANS (Neuro-ocular)    │  BioSample Engine         │
│     (Optic Ultrasound/MRI) │  (Blood, Urine, Saliva)   │
│                            │  SPA Web Dashboard        │
│  Delivers:                 │  (13 dark-theme screens)  │
│  ASTRA_MED_ML_PACKAGE.zip  │  Full Pytest Test Suite   │
└────────────────────────────┴───────────────────────────┘
```

---

## 2. Drop-In ML Predictor Interface Contract

Every ML module connects through the unified `MLPredictor` interface defined in `src/astra_med/ml/interface.py`:

```python
from astra_med.ml.interface import MLPredictor

class MyModelPredictor(MLPredictor):
    module_name = "cardiovascular"  # or immune, metabolic, radiation, neuromuscular, sans
    version = "1.0.0-trained"

    def predict(self, input_data: dict) -> dict:
        """Execute inference on sensor features or biomarker measurements."""
        return {
            "risk_label": "Elevated Orthostatic Drop",  # String label
            "confidence": 0.94,                        # 0.0 to 1.0
            "risk_score": 0.78,                        # 0.0 to 1.0
            "details": {                               # Module-specific breakdowns
                "qrs_ms": 94,
                "orthostatic_sys_drop_mmhg": 28.5
            }
        }

    def health_check(self) -> dict:
        return {
            "module": self.module_name,
            "status": "live",  # switches from "placeholder" to "live"
            "version": self.version
        }
```

### Hot-Swapping Models at Runtime
You can hot-swap any module dynamically without restarting the server:

```python
from astra_med.api.deps import get_ml_router
from your_module import TrainedCardioPredictor

router = get_ml_router()
router.swap_module("cardiovascular", TrainedCardioPredictor())
```

---

## 3. Quick Start & Execution

### Prerequisites
Python 3.10+ (tested on Python 3.14). Dependencies are pinned in `requirements.txt`.

### 1. Run the ASTRA-MED Server
```powershell
# From project root:
$env:PYTHONPATH="src"
python -m uvicorn astra_med.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser to:
- **Interactive Mission Dashboard:** `http://localhost:8000/`
- **FastAPI OpenAPI Swagger Documentation:** `http://localhost:8000/docs`
- **System Health Status:** `http://localhost:8000/api/v1/status`

### 2. Run the Verification Test Suite
```powershell
$env:PYTHONPATH="src"
python -m pytest tests/ -v
```

---

## 4. Key Directory Layout

```
SpaceHealthX/
├── docs/
│   ├── BLUEPRINT.md                 # Canonical mission specification & 5 hazards
│   ├── ARCHITECTURE.md              # 6-stage lifecycle (DETECT -> ADJUST)
│   ├── CONSTRAINTS_AND_SAFETY.md    # The 10 flight invariants
│   └── MASTER_DATASET_REGISTER.md   # Data pedigree catalog (Tier 1 to 5)
├── src/
│   └── astra_med/
│       ├── config.py                # Offline configuration settings
│       ├── core/
│       │   ├── types.py             # Pydantic models & domain Enums
│       │   ├── baseline.py          # Welford online personal baseline engine
│       │   ├── alert_engine.py      # Tri-color severity classification
│       │   ├── action_cards.py      # Pre-approved action card registry
│       │   └── store_forward.py     # Asynchronous delayed encounter packager
│       ├── db/
│       │   ├── database.py          # Async SQLAlchemy engine (SQLite)
│       │   ├── models.py            # ORM tables
│       │   └── crud.py              # Async CRUD operations
│       ├── ml/
│       │   ├── interface.py         # Abstract MLPredictor base class
│       │   ├── router.py            # Central ML router & hot-swapper
│       │   └── placeholders/        # 6 placeholder predictors
│       └── api/
│           ├── main.py              # FastAPI application entrypoint
│           ├── deps.py              # Dependency injection singletons
│           ├── auth.py              # Offline JWT utilities
│           └── routes/              # Modular REST API endpoints
├── action_cards/                    # Pre-authorized JSON action cards
├── frontend/
│   ├── index.html                   # Mission control SPA shell
│   └── static/
│       ├── css/main.css             # Dark-theme deep space stylesheet
│       └── js/                      # Modular vanilla JS (API, Components, Router, App)
└── tests/                           # Unit, integration & constraint verification tests
```

---

## 5. Non-Negotiable Flight Constraints

1. **Total Autonomous Offline Operation:** Zero cloud or external network dependencies.
2. **Asynchronous Communications:** Built for ~20-minute speed-of-light Mars latency.
3. **No Autonomous Drug Substitution:** Pre-authorized, static protocols only.
4. **Zero Unsupported Disease Diagnoses:** Outputs objective physiological deviations and functional adaptation states.
5. **Zero Real-Time Dependency for Emergencies:** Immediate onboard countermeasures.
6. **Personalized Baselines:** Evaluated against astronaut's own nominal data.
7. **Baseline Freezing During Anomalies:** Frozen on AMBER/RED alerts to prevent drift.
8. **Safety-Bounded Rehabilitation:** Hard limits on exercise and orthostatic stress.
9. **Tamper-Evident Audit Logging:** Cryptographic SHA-256 checksums on all encounters.
10. **Hardware-Decoupled Quality Control:** Signal Quality Index (SQI) verification prior to baseline ingestion.
