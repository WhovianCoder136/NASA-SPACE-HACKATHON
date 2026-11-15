# ASTRA-MED: Master Dataset Register & Data Pedigree Catalog

This catalog tracks all primary, secondary, and contextual datasets identified for training, evaluating, and bench-testing ASTRA-MED.

## Data Pedigree Classification Hierarchy
To prevent training contamination and invalid flight readiness claims:
- **Tier 1 (Flight):** Actual human astronaut in-flight / post-flight spaceflight data.
- **Tier 2 (Analogue):** Human ground-based microgravity / confinement analogues (e.g. 6° Head-Down Tilt Bed Rest, Antarctica, HERA, NEK).
- **Tier 3 (Modeled Microgravity):** In-vitro human cells cultured in rotating wall vessels, clinostats, or random positioning machines.
- **Tier 4 (Pre-clinical Flight/Ground):** Non-human animal spaceflight or ground studies (e.g. rodent spaceflight tissue).
- **Tier 5 (Terrestrial Clinical):** Terrestrial clinical cohorts (e.g. ICU, cardiology, sleep clinics).

---

## 1. Cardiovascular & Hemodynamic Datasets

| Accession / Name | Source | Organism | Pedigree Tier | Primary Variables / Modalities | Access Protocol | Target ASTRA-MED Pipeline |
|---|---|---|---|---|---|---|
| **PRCP** (Posture, Respiratory, Cardiac Physiology) | PhysioNet | *Homo sapiens* (n=10) | **Tier 5** (Terrestrial Posture Shift) | Continuous arterial blood pressure (Finapres), single-lead ECG, respiration during sit-to-stand posture transitions. | Public Open (PhysioNet) | GAR Module: Orthostatic hypotension detection, acute hemodynamic posture change classification. |
| **PTB-XL** | PhysioNet | *Homo sapiens* (n=18,885) | **Tier 5** (Terrestrial Clinical) | 10-second 12-lead clinical ECG waveforms, 500 Hz, curated diagnostic statements & wave annotations. | Public Open (PhysioNet) | Cardiovascular Module: Pan-Tompkins QRS benchmark, baseline rhythm stability, morphological feature extraction. |
| **MIT-BIH Arrhythmia** (mitdb) | PhysioNet | *Homo sapiens* (n=47) | **Tier 5** (Terrestrial Clinical) | Two-channel continuous ambulatory ECG recordings, beat-by-beat manual annotations. | Public Open (PhysioNet) | Cardiovascular Module: Ectopic beat rejection, arrhythmia alert triggers, RR-interval extraction. |
| **NASA BRSMCF** | NASA LSDA | *Homo sapiens* | **Tier 2** (Bed-Rest Analogue) | Bed-rest study cardiovascular function data, continuous HR, BP during prolonged inactivity. | NASA DDL / LSDA Request Required | GAR Module: Long-duration deconditioning trajectory modeling. |
| **NASA Tilt Test** | NASA LSDA | *Homo sapiens* | **Tier 2** (Bed-Rest / Orthostatic Challenge) | Heart rate, blood pressure, stroke volume, cardiac output during passive tilt testing. | NASA DDL / LSDA Request Required | GAR Module: Passive orthostatic tilt tolerance & syncope prediction. |
| **OSD-580** | NASA OSDR | *Mus musculus* | **Tier 4** (Animal Spaceflight) | RNA-seq profiling of mouse cardiac tissue after spaceflight. | Public Open (NASA OSDR) | Molecular Context: Gene expression alterations under microgravity. *Not for ECG or clinical BP modeling.* |

---

## 2. Hostile Environments: Immune System & Viral Reactivation

| Accession / Name | Source | Organism | Pedigree Tier | Primary Variables / Modalities | Access Protocol | Target ASTRA-MED Pipeline |
|---|---|---|---|---|---|---|
| **OSD-569** | NASA OSDR | *Homo sapiens* | **Tier 1** (Human Flight) | Complete blood count (CBC) and whole-blood molecular signatures in astronauts. | Public Open (OSDR Metadata) | BioSample / Immune: Astronaut baseline leukocyte shifts and hematology norms. |
| **OSD-570** | NASA OSDR | *Homo sapiens* | **Tier 1** (Human Flight) | T-cell and B-cell immunophenotyping, molecular regulation post-flight. | Public Open (OSDR Metadata) | Immune Module: Adaptive immunity suppression scoring. |
| **OSD-575** | NASA OSDR | *Homo sapiens* | **Tier 1** (Human Flight) | Multiplexed circulating cytokines, systemic inflammation, metabolic markers. | Public Open (OSDR Metadata) | BioSample / Immune: Inflammatory cascade detection (IL-6, TNF-alpha baseline deviations). |
| **OSD-53** | NASA OSDR | *Homo sapiens* | **Tier 1** (Human Flight) | Astronaut whole-blood microRNA and transcriptomic profiles. | Public Open (OSDR) | Molecular Context: In-flight genomic stress response. |
| **OSD-5** | NASA OSDR | *Homo sapiens* | **Tier 3** (Modeled Microgravity) | Human peripheral blood T-cell activation in modeled microgravity. | Public Open (OSDR) | Immune Module: Early cellular inactivation dynamics. |
| **OSD-55** | NASA OSDR | *Homo sapiens* | **Tier 1** (Human Flight) | Lymphocyte microRNA expression in spaceflight crew. | Public Open (OSDR) | Immune Module: Epigenetic immune modulation tracking. |
| **OSD-54** | NASA OSDR | *Homo sapiens* | **Tier 1/3** (Ground/Flight Stimulated) | In-vitro stimulated human immune response in spaceflight environment. | Public Open (OSDR) | Immune Module: Cytokine synthesis capacity validation. |

---

## 3. Gravity Adaptation & Rehabilitation (GAR) Specific Datasets

| Accession / Name | Source | Pedigree Tier | Primary Modalities | Status | Notes |
|---|---|---|---|---|---|
| **PRCP** | PhysioNet | Tier 5 | Continuous BP + ECG sit/stand | Verified / Ready | Primary baseline for orthostatic transition detector. |
| **NASA BRSMCF** | NASA LSDA | Tier 2 | Bed-rest cardiovascular parameters | Access Request Needed | Ground-truth for cardiovascular deconditioning. |
| **NASA Tilt Test** | NASA LSDA | Tier 2 | Stroke volume, cardiac output during tilt | Access Request Needed | Standard reference for tilt-table tolerance testing. |
| **Dynamic Gait & Postural Sway Register** | PhysioNet / Synthetic Bench | Tier 5 | Force plate center-of-pressure (CoP), 3D IMU accelerometry | Sourcing in progress | Required for Post-Transition locomotion & balance assessment. |

---

## 4. Space Radiation Datasets

| Category | Variables Monitored | Candidate Accessions / Sources | Data Pedigree |
|---|---|---|---|
| **Dosimetry & Absorbed Dose** | Real-time absorbed dose rate ($\mu\text{Gy/h}$), cumulative Sievert equivalents, LET spectra. | NASA MSL RAD Mars transit/surface logs; ISS Liulin dosimeter logs. | Flight telemetry (Tier 1/In-situ robotic). |
| **DNA Damage & Repair** | $\gamma\text{H2AX}$ foci count, 53BP1 kinetics, chromosomal aberrations. | NASA OSDR radiation biology collections, human lymphoblastoid radiation assays. | Tier 3 / Tier 5. |
| **Oxidative Stress Biomarkers** | 8-hydroxy-2'-deoxyguanosine (8-OHdG), malondialdehyde (MDA), total antioxidant capacity. | NASA OSDR flight urine/blood metabolomics (OSD-575 subset). | Tier 1. |

---

## 5. Isolation, Confinement & Circadian Datasets

| Category | Variables Monitored | Candidate Accessions / Sources | Data Pedigree |
|---|---|---|---|
| **Circadian & Sleep Architecture** | Polysomnography (PSG), continuous wrist actigraphy, circadian phase angle, sleep efficiency. | NASA Mars-500 isolation telemetry, HERA campaign data, PhysioNet Sleep-EDF. | Tier 2 (Confinement) & Tier 5. |
| **Neurobehavioral & Cognitive** | Psychomotor Vigilance Task (PVT-10m / PVT-3m), Cognition battery, reaction latency, lapses (>500ms). | NASA LSDA HERA missions, NASA Flight Cognition logs. | Tier 1 & Tier 2. |
| **Stress & Salivary Biomarkers** | Diurnal salivary cortisol slope, salivary alpha-amylase, subjective mood ratings. | Mars-500 biochemical logs, Antarctic Concordia station cohorts. | Tier 2. |

---

## 6. Contextual & Supporting NASA Research Datasets

| Accession | Research Focus | Organism | Notes |
|---|---|---|---|
| **OSD-815, 816, 817, 818** | Spaceflight-Associated Neuro-ocular Syndrome (SANS) & ocular models | Mixed / Ex-vivo | Contextual for ocular / tear fluid roadmap. |
| **OSD-977 / GLDS-345** | Bone loss and osteoclast regulation in microgravity | Rodent / Cell | Contextual for long-duration skeletal remodeling. |
| **OSD-326 / GLDS-326** | Muscle atrophy and protein synthesis under microgravity | Rodent | Contextual for exercise conditioning countermeasure evaluation. |

---

## 7. BioSample Intelligence Engine: Target Specimen Matrix

| Specimen | Analyte Group | Target Analytes | Instrument Assay Category |
|---|---|---|---|
| **Peripheral Blood** | Complete Blood Count (CBC) | RBC, Hgb, Hct, MCV, Platelet count, total WBC. | Automated microfluidic impedance / optical cytometer. |
| | Differential & Immune Subsets | Neutrophils, Lymphocytes, Monocytes, Eosinophils, Basophils, CD4/CD8 ratio, NK cells. | Miniaturized micro-flow cytometer. |
| | Cytokine Cascade | IL-6, TNF-$\alpha$, IL-1$\beta$, IFN-$\gamma$, IL-10. | Multiplexed planar bead array / SPR biosensor. |
| | Metabolic & Electrolytes | $\text{Na}^+, \text{K}^+, \text{Cl}^-, \text{Ca}^{2+}$, Glucose, Lactate, BUN, Creatinine. | Point-of-care dry-chemistry cartridge. |
| **Urine** | Physical & Chemical | Specific gravity, osmolality, pH, Protein, Glucose, Ketones. | Optical refractometer + test strip reflectometer. |
| | Renal & Electrolytes | Creatinine, Calcium, Sodium, Potassium, Uric Acid. | Micro-volume enzymatic cartridge. |
| **Saliva** | Neuroendocrine & Stress | Free Cortisol (morning wake-up vs bedtime slope), Secretory IgA. | Lateral flow reader / competitive immunoassay. |
| | Viral Shedding | DNA copy numbers: EBV, VZV, HSV-1, TTV. | Isothermal nucleic acid amplification (LAMP/micro-PCR). |
