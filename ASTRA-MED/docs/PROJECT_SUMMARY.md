# ASTRA-MED: Comprehensive Project Summary & System Documentation

**Autonomous Deep-Space Health & Acclimatization System**
*Mission Context: Crewed Mars Exploration Mission (3-Year Mission, 6–9 Month Transit, ~20-Minute Light-Speed Comms Delay)*

---

## 1. Executive Summary

**ASTRA-MED** is an autonomous, offline-first clinical decision-support and physiological monitoring system engineered specifically for long-duration deep-space human spaceflight.

During an interplanetary transit to Mars, physical distance creates a one-way communication latency between 6 and 22 minutes (nominally **~20 minutes**). This fundamental physical constraint renders traditional real-time terrestrial telemedicine and emergency consultation impossible. An acute medical condition or rapid physiological deconditioning must be triaged, stabilized, and monitored by the onboard crew autonomously.

ASTRA-MED serves as the crew's onboard clinical partner. It autonomously tracks multidimensional health data, evaluates deviations against personalized pre-flight baselines, generates objective non-diagnostic clinical insights, executes safety-bounded countermeasure protocols, and manages asynchronous medical communications with Earth Ground Control.

---

## 2. NASA's 5 Human Spaceflight Hazards (RIDGE) Coverage

ASTRA-MED provides comprehensive operational and clinical coverage across all five NASA-identified human spaceflight hazards:

```
                            ┌──────────────────────────────────────────┐
                            │           ASTRA-MED PLATFORM             │
                            └────────────────────┬─────────────────────┘
                                                 │
        ┌───────────────────┬────────────────────┼───────────────────┬───────────────────┐
        ▼                   ▼                    ▼                   ▼                   ▼
1. Space Radiation   2. Isolation &      3. Distance from    4. Hostile / Closed  5. Altered Gravity
   - Dosimetry          Confinement         Earth               Environments         Fields
   - Cumulative mSv  - Sleep duration    - Offline autonomy  - Air/water tox     - Orthostatic BP
   - DNA repair         & architecture   - Store & Forward   - Pathogen shedding - Muscle atrophy
   - GCR / SPE alarm - Circadian drift     (20-min delay)    - Biosample QC      - Gait stability
                     - PVT lapses        - SHA-256 packets                       - SANS (ONSD, OCT)
```

### Hazard 1: Space Radiation
- **Threat Profile:** Galactic Cosmic Rays (GCR) and Solar Particle Events (SPE) damage DNA, elevate carcinogenesis risks, and induce acute radiation syndromes.
- **Monitoring & Biomarkers:** Active dosimeter flux rates, cumulative mission dose in millisieverts (mSv), DNA damage/repair markers ($\gamma$-H2AX), and oxidative stress indicators.
- **Onboard Action:** Immediate high-flux shelter alarms and cell-protective recovery protocols.

### Hazard 2: Isolation & Confinement
- **Threat Profile:** Circadian misalignment, sleep disruption, neurocognitive fatigue, and elevated psychological stress.
- **Monitoring & Biomarkers:** Sleep architecture (total sleep time, REM %, deep sleep %), circadian phase shifts, and Psychomotor Vigilance Task (PVT) reaction lapses.
- **Onboard Action:** Circadian phase-shifting lighting recommendations, cognitive workload adaptation, and non-pharmacological sleep hygiene protocols.

### Hazard 3: Distance from Earth
- **Threat Profile:** Total physical isolation with no evacuation capability and up to 44-minute round-trip communication delays.
- **System Architecture:** 100% offline edge-computing execution, asynchronous Store-and-Forward transmission buffers, and cryptographic medical encounter packaging.

### Hazard 4: Hostile / Closed Environments
- **Threat Profile:** Immunological dysregulation, subclinical viral reactivation, closed-loop life support chemical build-ups, and metabolic imbalances.
- **Monitoring & Biomarkers:** White blood cell differentials, C-reactive protein (CRP), inflammatory cytokines, metabolic panels (glucose, electrolytes, lactate), and automated biosample quality controls.

### Hazard 5: Altered Gravity Fields
- **Threat Profile:** Headward fluid shifts, cardiovascular deconditioning, orthostatic intolerance, sensorimotor ataxia, muscle atrophy, bone mineral density loss, and Spaceflight-Associated Neuro-ocular Syndrome (SANS).
- **Monitoring & Biomarkers:** Postural orthostatic systolic/diastolic blood pressure drops, heart rate variability (HRV), isometric muscle strength, gait symmetry, Optic Nerve Sheath Diameter (ONSD), intraocular pressure (IOP), and optical coherence tomography (OCT) metrics.

---

## 3. The 10 Flight Invariants (Clinical Safety Constraints)

ASTRA-MED enforces ten non-negotiable safety rules in its code, API schemas, and user interfaces:

1. **Total Autonomous Offline Operation:** All data ingestion, anomaly detection, baseline tracking, and action card retrieval execute locally without requiring internet access or ground connectivity.
2. **Asynchronous Communications by Default:** System workflows assume communication latencies up to 20 minutes; no system thread or user workflow blocks awaiting ground response.
3. **Zero Autonomous Disease Diagnosis (`"diagnosis": null`):** The system strictly outputs objective physiological observations, statistical deviations, and functional readiness states. It is prohibited from generating speculative clinical diagnoses (e.g. diagnosing "Myocarditis").
4. **No Autonomous Drug Prescription:** The software never recommends drug substitutions, calculates novel dosages, or generates pharmacological prescriptions. All medical actions are pre-approved, non-pharmaceutical countermeasure protocols.
5. **Zero Real-Time Dependency for Acute Emergencies:** Emergency countermeasure workflows (e.g. syncope recovery, acute radiation shelter protocols) reside onboard and are immediately executable.
6. **Personalized Baseline Normalization:** All anomaly calculations use personalized moving baseline distributions calculated via the Welford online algorithm rather than terrestrial population averages.
7. **Automatic Baseline Freezing During Anomalies:** When an active AMBER or RED alert is triggered, baseline parameter updates automatically freeze to prevent pathological data from skewing the nominal baseline.
8. **Safety-Bounded Physical Protocols:** Rehabilitation and exercise regimens enforce physiological boundaries (e.g., target heart rate caps, blood pressure drop thresholds) and automatically command de-escalation if violated.
9. **Tamper-Evident Immutable Audit Trail:** Every measurement, checkup submission, alert acknowledgment, and telemetry packet is hashed using SHA-256 and recorded in an immutable audit ledger.
10. **Hardware-Decoupled Quality Control:** Biosamples and sensor streams must pass Signal Quality Index (SQI) and control validation before inclusion in clinical calculations.

---

## 4. The 6-Stage Clinical Processing Pipeline

```
  [1. DETECT]  ──► Real-time telemetry ingestion, SQI filtering, and personal baseline Z-score computation
       │
  [2. ALERT]   ──► Tri-color severity classification: GREEN (Nominal), AMBER (Mild/Moderate), RED (Critical)
       │
  [3. BRIDGE]  ──► Instant retrieval of pre-authorized, versioned Medical Action Cards (e.g. CARD-CVD-AMBER-01)
       │
  [4. SIGNAL]  ──► Assembly of encrypted Medical Encounter Packages (MEPs) with SHA-256 integrity checksums
       │
  [5. CONSULT] ──► Asynchronous Store-and-Forward queuing to Earth ground control (simulated 20-min delay)
       │
  [6. ADJUST]  ──► Onboard crew review and cryptographic authentication of ground-directed medical updates
```

---

## 5. System Architecture & Tech Stack

```
SpaceHealthX/
├── docs/                               # Engineering blueprints, flight constraints, architecture
│   ├── BLUEPRINT.md
│   ├── ARCHITECTURE.md
│   ├── CONSTRAINTS_AND_SAFETY.md
│   ├── MASTER_DATASET_REGISTER.md
│   └── PROJECT_SUMMARY.md              # Canonical project documentation
├── src/astra_med/
│   ├── config.py                       # Configuration & offline defaults
│   ├── core/                           # Clinical engines
│   │   ├── types.py                    # Domain models, Enums, and Pydantic schemas
│   │   ├── baseline.py                 # Welford online baseline engine with anomaly freezing
│   │   ├── alert_engine.py             # GREEN / AMBER / RED tri-color classifier
│   │   ├── action_cards.py             # Pre-authorized clinical countermeasure registry
│   │   └── store_forward.py            # Deep-space delayed encounter packager & hasher
│   ├── db/                             # Persistence tier
│   │   ├── database.py                 # SQLite + SQLAlchemy async engine (WAL mode)
│   │   ├── models.py                   # Relational ORM models (Crew, Checkups, Vitals, Reports)
│   │   ├── migrations.py               # Automated zero-data-loss database migration manager
│   │   └── crud.py                     # High-performance database operations
│   ├── ml/                             # Machine learning integration
│   │   ├── interface.py                # Drop-in MLPredictor abstract base contract
│   │   ├── router.py                   # Central ML router with runtime hot-swapping
│   │   └── placeholders/               # Predictor stubs with honest status reporting
│   └── api/                            # REST Application
│       ├── main.py                     # FastAPI lifespan application entry point
│       ├── auth.py                     # Offline JWT auth & bcrypt password hashing
│       ├── deps.py                     # Dependency injection singletons
│       └── routes/                     # REST API route controllers
├── frontend/                           # Deep space cockpit SPA
│   ├── index.html                      # HTML5 mission control application shell
│   └── static/
│       ├── css/main.css                # Dark-theme tactical CSS stylesheet
│       └── js/                         # Modular vanilla ES6 JS (API, Router, Views, Storage)
├── action_cards/                       # Pre-authorized JSON clinical action cards
├── data/                               # SQLite databases, automated backups, and file uploads
└── tests/                              # Complete Pytest automated verification suite (64 tests)
```

### Technology Highlights:
- **Backend:** **Python 3.10+ / 3.14** with **FastAPI** for asynchronous, high-throughput REST APIs and Pydantic v2 schemas.
- **Database:** **SQLite with Write-Ahead Logging (WAL)**. Includes an automated, idempotent migration engine (`src/astra_med/db/migrations.py`) tracking versions in `schema_migrations`, guaranteeing data preservation across application updates.
- **Frontend:** Vanilla modern **HTML5, CSS3, and ES6 JavaScript Single-Page Application (SPA)**. Built with zero external CDN or npm runtime dependencies to ensure 100% offline functionality. Features 13+ specialized views.
- **Authentication:** Offline JSON Web Tokens (JWT) using local secret signing keys and direct `bcrypt` password encryption. Enforces role segregation between standard Astronauts and Flight Medical Officers.

---

## 6. Subsystems & Operational Features

### A. Health Checkup & Medical Records Intake
- **Multi-Domain Forms:** Interactive entry for vitals, cardiovascular hemodynamics, immune panels, metabolic markers, radiation exposure, sleep logs, neuromuscular strength, and SANS vision metrics.
- **Diagnostic File Attachments:** Direct upload and server-side storage for 12-lead ECG recordings, ultrasound/OCT optical scans, and clinical laboratory PDFs, each tagged with SHA-256 hashes.
- **Offline Client Buffering:** Astronaut submissions made during hardware disconnection are queued in local browser storage and seamlessly synchronized upon reconnection via `/api/v1/checkups/sync`.
- **Idempotent Deduplication:** Every submission carries a unique `client_checkup_id` preventing accidental duplicate record creation.

### B. Personal Baseline & Anomaly Engine
- Employs **Welford's algorithm** to compute running mean ($\mu$) and standard deviation ($\sigma$) with minimal memory footprint.
- Incoming measurements are converted into standardized deviation scores ($Z = (x - \mu)/\sigma$).
- If an active anomaly is detected, updates are instantly suspended to avoid incorporating pathological states into baseline metrics.

### C. Action Card Registry
- Contains versioned, physician-authored protocols for physical countermeasures:
  - `CARD-CVD-AMBER-01`: Cardiovascular Orthostatic Deconditioning Countermeasure (LBNP + salt/fluid loading).
  - `CARD-RAD-AMBER-01`: Elevated Radiation Protocol (storm shelter ingress, DNA protectant regimen).
  - `CARD-SLEEP-AMBER-01`: Circadian Misalignment & Fatigue Mitigation (blue-light scheduling, sleep window alignment).
  - Pre-approved cards for Immune, Metabolic, Neuromuscular, and SANS modules.

### D. Deep-Space Store-and-Forward Simulator
- Encapsulates health checkups and critical alerts into serialized **Medical Encounter Packages (MEPs)**.
- Simulates the physical Mars-to-Earth 20-minute (1,200-second) transit delay.
- Enables ground flight surgeons to review telemetry asynchronously and transmit cryptographically signed protocol modifications back to the spacecraft.

---

## 7. Verification & Quality Assurance Report

The entire ASTRA-MED platform is backed by a 64-test automated verification suite:

```
============================= 64 passed in 4.69s ==============================
```

| Test File | Tests | Functional Scope Covered |
| :--- | :---: | :--- |
| `tests/test_e2e_full.py` | 10 | End-to-end mission workflows: login, profile management, checkup submission, module routing, baseline analysis, action cards, comms delay, and security boundaries. |
| `tests/test_health_checkups.py` | 15 | Multi-domain clinical intake, file uploads (ECG, PDF, Ultrasound), idempotent duplicate handling, boundary checks, and offline sync. |
| `tests/test_startup_and_schema.py` | 7 | Automated SQLite migrations, table integrity checks, schema validation, and credential preservation. |
| `tests/test_constraints.py` | 5 | Verification of the 10 flight constraints (offline capability, non-diagnostic output, baseline freezing, audit logging). |
| `tests/test_core.py` | 6 | Welford algorithm accuracy, alert severity thresholds, and store-and-forward integrity hashing. |
| `tests/test_api.py` | 8 | REST endpoints, vitals ingestion, action card lookups, and JWT session handling. |
| `tests/test_ml.py` | 9 | Drop-in `MLPredictor` interface, dynamic model hot-swapping, and module health checks. |
| `tests/test_new_engines.py` | 4 | Insight engine diagnostic restrictions, action cards, and unified measurement overviews. |

---

## 8. Current Deployment Status & Future Roadmap

- **Core Infrastructure & Web Platform:** **Production-Ready & Fully Functional.**
- **Heuristics & Rule Engines:** **Operational.** The Sleep & Circadian engine (`v1.0.0-heuristic`) actively evaluates sleep stages and reaction lapses. Baseline $Z$-score tracking is active across all parameters.
- **ML Predictor Hot-Swapping:** Cardiovascular, Immune, Metabolic, Radiation, Neuromuscular, and SANS interfaces are deployed with honest `status="placeholder"`. They are fully prepared to receive trained binary model packages (`ASTRA_MED_ML_PACKAGE.zip`) through the standardized `MLPredictor` drop-in contract without requiring server restarts or backend refactoring.
- **Hardware Integration:** Standardized ingestion endpoints are ready for integration with continuous physiological telemetry streams and point-of-care medical hardware devices.
