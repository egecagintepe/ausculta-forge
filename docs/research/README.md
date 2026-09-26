# AuscultaForge — Scientific Research Foundation & Literature Governance

## 1. Purpose & Governance

AuscultaForge is an engineering and scientific research platform for digital phonocardiography (PCG), acoustic phantom validation, and biomedical signal analysis.

To prevent academic dilution, undocumented heuristics, or fabricated medical claims, **all signal-processing and analysis algorithms in AuscultaForge must be grounded in peer-reviewed literature and rigorous discrete-time signal processing theory**.

From this milestone onward, every algorithm follows the **AuscultaForge Traceability Chain**:

```text
Physical Problem
       │
       ▼
Mathematical Model
       │
       ▼
Assumptions & Validity Conditions
       │
       ▼
Literature Source / Citation
       │
       ▼
Algorithm & Parameter Configuration
       │
       ▼
Deterministic Software Implementation
       │
       ▼
Deterministic Automated Unit Tests
       │
       ▼
Versioned Provenance & Metadata
       │
       ▼
UI Visual Presentation & Scientific Interpretation
```

---

## 2. Directory Structure

```text
docs/research/
├── README.md                     # This document: governance & research directory map
├── SOURCE_REGISTRY.md            # Authoritative index of literature sources (R001–R008)
├── THEORY_MAP.md                 # Physical acoustic chain to mathematical abstractions
├── ALGORITHM_DECISIONS.md        # Decision records: CORE_NOW, NEXT_DSP, RESEARCH_LATER, REJECTED
├── SCIENTIFIC_CONVENTIONS.md     # 3-representation model, sampling policies, automatic analysis
├── MATH_CONVENTIONS.md           # Rigorous mathematical definitions and notation
├── UNITS_AND_CALIBRATION.md      # Strict units policy (prohibition of uncalibrated Pa/dB SPL)
├── ANALYSIS_PROFILES.md          # Versioned scientific configurations (RAW, GENERAL, PHANTOM, etc.)
├── RESEARCH_BACKLOG.md           # Open research gaps requiring formal literature grounding
└── sources/                      # Individual source dossier cards (R001–R008)
    ├── R001-rangayyan-biomedical-signal-analysis.md
    ├── R002-oppenheim-discrete-time-signal-processing.md
    ├── R003-heinzel-spectrum-estimation.md
    ├── R004-welch-power-spectrum-estimation.md
    ├── R005-schmidt-duration-dependent-hmm.md
    ├── R006-springer-logistic-regression-hsmm.md
    ├── R007-liu-hsmm-independent-database-evaluation.md
    └── R008-rangayyan-biomedical-image-analysis.md  (LOW DIRECT RELEVANCE)
```

---

## 3. Algorithm Status Classification

No mathematical formulation or parameter is introduced simply because "a paper uses it". Every candidate algorithm receives one of five explicit classifications:

| Status | Meaning | Current Examples |
|---|---|---|
| **`CORE_NOW`** | Fully implemented, mathematically verified, covered by deterministic tests, and active in production. | Butterworth bandpass, Welch PSD, cross-correlation alignment, least-squares gain, RMSE, SER dB, magnitude-squared coherence, peak-preserving display decimation. |
| **`NEXT_DSP`** | Scientifically approved for immediate development in subsequent milestones; source citations established. | Hilbert envelope, homomorphic envelope, RMS envelope, candidate acoustic event detection, duration features. |
| **`RESEARCH_LATER`** | Under active literature review; requires formal mathematical modeling before implementation. | Logistic-Regression Hidden Semi-Markov Model (LR-HSMM), modified Viterbi decoding, frequency response function estimators ($H_1, H_2$). |
| **`THESIS_ONLY`** | Background theory, comparative analysis, or thesis narrative; not part of real-time application code. | Continuous-time acoustic wave propagation in chest tissue, physiological origin of S3/S4 sounds, historical analog stethoscopes. |
| **`REJECTED`** | Formally considered and rejected due to methodological, physical, or academic invalidity. | Automated AI clinical diagnosis without physiological reference labels, black-box quality scores ("85/100 healthy"), uncalibrated $\text{Pa} / \text{dB SPL}$ reporting, naive downsampling without anti-aliasing. |

---

## 4. Fundamental Triad: Three Signal Representations

AuscultaForge enforces an absolute architectural separation across three distinct representations of audio signals:

1. **ACQUISITION SIGNAL:**
   The master digital stream at the hardware boundary (Hardware Rev-A: 48 kHz, mono, signed 24 transmitted bits in 32-bit container), ingested as normalized full-rate float32 `SampleBlock` sequences on the host and preserved in full-rate float32 WAV session recordings.
2. **ANALYSIS SIGNAL:**
   An explicitly processed, filtered, or resampled representation used for a declared engineering task (e.g. 20–600 Hz bandpass, or 1000 Hz downsampled feature stream). Parameterized strictly via versioned `AnalysisProfile` declarations.
3. **DISPLAY SIGNAL:**
   A bounded, decimated representation ($\le 600$ points) computed via peak-preserving min/max aggregation (`decimate_aligned_traces_shared_time`) strictly used for UI visual rendering. **Display data never enters quantitative metric calculations.**

---

## 5. Contact & Maintenance

All updates to these research documents require peer-review against primary literature sources. Do not cite secondary summaries or fabricate page numbers. When a specific page number cannot be verified, cite the formal chapter and section title.
