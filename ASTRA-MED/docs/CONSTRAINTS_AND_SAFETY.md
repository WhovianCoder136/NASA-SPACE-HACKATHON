# ASTRA-MED: Clinical Safety Invariants & Engineering Constraints

## The 10 Flight Constraints

Every algorithm, module, pipeline, and UI component in ASTRA-MED must strictly enforce the following 10 constraints:

1. **Total Autonomous Offline Operation:**
   The full monitoring pipeline, anomaly detection algorithms, baseline comparisons, and action card retrieval systems must execute 100% locally on spacecraft compute without internet, cloud dependencies, or ground connectivity.

2. **Asynchronous Communications by Default:**
   All interactions with Earth ground control must assume variable store-and-forward transmission delays (e.g. 6 to 22 minutes one-way, ~20 min nominal). No system block or synchronous request may ever wait for ground response.

3. **No Autonomous Drug Substitution or Pharmacological Reasoning:**
   ASTRA-MED must NEVER autonomously recommend drug substitutions, adjust prescription dosages, or generate novel pharmacological regimens. Medication guidance is restricted strictly to pre-authorized, physician-authored, static Action Cards with human crew verification.

4. **Zero Unsupported Disease Diagnosis:**
   The software must never present speculative disease labels (e.g., "Infection detected: Pneumonia") to crew members. The system outputs objective physiological deviations, biomarker shifts, and functional adaptation states (e.g., "Leukocyte count +3.2σ, elevated IL-6, fever trend; Functional Status: Systemic Inflammatory Elevation - Requires Clinical Protocol 402").

5. **Zero Real-Time Dependency for Acute Emergencies:**
   Emergency stabilization instructions, syncope prevention, acute arrhythmia triage, or radiation shelter procedures must be fully onboarded and immediately executable without ground intervention.

6. **Personalized, Quality-Controlled Baselines:**
   Deviations must be measured against the individual astronaut's verified personal baseline, not generalized terrestrial population averages. Baselines must be initialized during pre-flight and early-flight periods using only high-quality, artifact-free data.

7. **Baseline Freezing During Anomalous States:**
   When an active alert (AMBER or RED) is flagged, or when signal quality drops below acceptable thresholds, the baseline update engine MUST automatically freeze. Baselines must never silently drift or adapt to include pathological measurements.

8. **Safety-Bounded Exercise & Rehabilitation Progression:**
   Physical exercise prescriptions, orthostatic challenges, and rehabilitation loading must follow strict NASA-approved physiological boundaries (e.g. maximum target heart rate zones, rate of blood pressure drop cutoffs). When thresholds are exceeded, the system immediately commands protocol de-escalation.

9. **Tamper-Evident Immutable Audit Logging:**
   All raw telemetry, quality scores, detected deviations, crew acknowledgments, displayed action cards, and ground telemetry packets must be recorded in an immutable, cryptographically verifiable local audit log.

10. **Hardware-Decoupled Analytical Quality Control:**
    The software does not assume flawless instrument performance. All incoming biosample measurements must pass explicit quality control validation (dilution, temperature, control bead verification) before being ingested into the clinical reasoning pipeline.
