# ASTRA-MED: Core Software Architecture & Clinical Decision Pipeline

## 1. The 6-Stage Processing Lifecycle

All five hazard modules implement a strictly unified 6-stage lifecycle:

```
  [1. DETECT]
       │  (Ingest telemetry, validate signal quality, compare vs personal baseline)
       ▼
  [2. ALERT]
       │  (Tri-color severity classification: GREEN, AMBER, RED; rule-based, no unsupported diagnosis)
       ▼
  [3. BRIDGE]
       │  (Fetch pre-authorized, versioned Action Card for immediate crew execution)
       ▼
  [4. SIGNAL]
       │  (Assemble encrypted Medical Encounter Package, queue in store-and-forward buffer)
       ▼
  [5. CONSULT]
       │  (Asynchronous downlink to Mission Control Flight Surgeon; handle 20-min speed-of-light delay)
       ▼
  [6. ADJUST]
          (Crew-verified update ingestion; cryptographically signed medical updates applied safely)
```

---

### Stage 1: DETECT
- **Telemetry Ingestion:** Receives continuous or intermittent datastreams from wearables (ECG, photoplethysmography), point-of-care biosample analyzers, environmental sensors, and neurobehavioral test consoles.
- **Signal Quality Index (SQI) Check:** Before any numerical metric is computed, raw signals are filtered for motion artifacts, sensor detachment, or dilution errors. Unreliable data is flagged and excluded from baseline calculations.
- **Personal-Baseline Comparison:** Normalizes incoming metrics against the astronaut's nominal moving baseline window ($W_{nominal}$, typically 14–30 nominal days). Calculates deviation metric $\Delta = (x_t - \mu_{base}) / \sigma_{base}$.

### Stage 2: ALERT
- Categorizes deviation into one of three clinical severity tiers:
  - **GREEN (Nominal / Stable):** Metric within normal expected physiological variability ($\pm 2\sigma$). Action: Continuous logging, zero crew interruption.
  - **AMBER (Mild-to-Moderate Deviation / Early Intervention):** Persistent deviation detected across multiple samples or sustained periods (e.g., orthostatic drop, early viral shedding, rising inflammatory markers, circadian drift). Action: Crew notification, reversible countermeasure recommendation, standard consult packaging.
  - **RED (Critical Deviation / Acute Risk):** Critical threshold breached requiring immediate crew stabilization (e.g., severe acute orthostatic syncope risk, profound arrhythmia, acute radiation event biomarker spike). Action: High-priority multimodal alarm, immediate life-support / stabilization action card display, priority comms queuing.
- **Strict Clinical Invariant:** Under NO circumstances does the system present speculative disease diagnoses (e.g., "Crew member has Myocarditis"). It presents objective physiological deviations and validated functional statuses (e.g., "Orthostatic Systolic BP drop >28 mmHg with sinus tachycardia; Adaptation Status: Incomplete Adaptation").

### Stage 3: BRIDGE
- Automatically retrieves an immutable, pre-approved, versioned **Medical Action Card** corresponding to the detected state.
- Cards provide clear, step-by-step, plain-language guidance:
  - Physical countermeasures (e.g., lower-body negative pressure protocol adjustment, hydration salt-tablet loading, specialized vestibular recalibration drills).
  - Diagnostic confirmation steps (e.g., "Collect repeat saliva sample in 12 hours for verification").
  - Crew safety checks (e.g., "Do not operate extravehicular mobility unit or piloting controls until orthostatic stability is confirmed").

### Stage 4: SIGNAL
- Packages the complete clinical event into an autonomous **Medical Encounter Package (MEP)**:
  - Subject ID (anonymized onboard token)
  - Timestamp (Mission Elapsed Time - MET)
  - Raw signal slice + SQI report
  - Extracted feature vector & personal baseline parameters
  - Triggering threshold & Alert tier
  - Action card ID presented to crew & crew acknowledgment state
  - Local checksum and cryptographic signature
- Stores the MEP in local persistent SQLite/append-only storage.

### Stage 5: CONSULT
- Buffers packages in the outbound Store-and-Forward transmission queue.
- Transmits data through high-gain deep-space communication links whenever contact windows open, accounting for the 20-minute light delay.
- Enables ground flight surgeons to review the identical data stream seen onboard.

### Stage 6: ADJUST
- Receives ground medical recommendations, protocol adjustments, or updated action cards during return transmission windows.
- **Safety Gate:** Incoming updates require secondary onboard authentication and explicit crew approval. Emergency stabilization procedures CANNOT be silently overwritten or disabled over the wire while active.

---

## 2. Gravity Adaptation & Rehabilitation (GAR) Three-Phase Lifecycle

Gravity transition is a primary focal point of ASTRA-MED. The GAR module operationalizes adaptation across 3 operational mission phases:

1. **PRE-TRANSITION (Late Microgravity Transit):**
   - High-fidelity baseline characterization.
   - Directed countermeasure intensification (resistive exercise, fluid loading readiness).
   - Cardiovascular conditioning and autonomic tone evaluation.
2. **TRANSITION (Orbital Insertion / Planetary Landing / Ingress):**
   - Continuous hemodynamics tracking during acute gravitational reload ($0g \to 0.38g$ or $0.38g \to 0g$).
   - Postural shift challenge (Sit-to-stand / tilt equivalent).
   - Acute sensorimotor & vestibular ataxia assessment.
3. **POST-TRANSITION (Surface Habitation / Readaptation):**
   - Dynamic locomotion and gait symmetry evaluation.
   - Vestibulo-ocular reflex (VOR) gaze fixation tracking.
   - Functional adaptation scoring:
     - `ADAPTATION_OPTIMAL`
     - `ADAPTATION_PROGRESSING`
     - `ADAPTATION_INCOMPLETE`
     - `REQUIRES_CLINICAL_ASSESSMENT`
