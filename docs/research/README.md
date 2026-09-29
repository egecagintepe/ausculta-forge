# Scientific Research Foundation & Literature Governance
## Smart Digital Stethoscope: Heart Sound Acquisition, Signal Processing and Quality Assessment
### EEE495 / EEE496 Senior Design Project (Platform / Software Codename: `AuscultaForge`)

## 1. Purpose & Governance

AuscultaForge is the software and engineering research platform for the digital phonocardiography (PCG), acoustic phantom validation, and biomedical signal analysis subcomponents of the Senior Design Project.

To prevent academic dilution, undocumented heuristics, or fabricated medical claims, **all signal-processing and analysis algorithms in AuscultaForge must be grounded in peer-reviewed literature and rigorous discrete-time signal processing theory**.

From this milestone onward, every algorithm follows the **AuscultaForge Traceability Chain**:

```text
Physical Problem
       â”‚
       â–¼
Mathematical Model
       â”‚
       â–¼
Assumptions & Validity Conditions
       â”‚
       â–¼
Literature Source / Citation
       â”‚
       â–¼
Algorithm & Parameter Configuration
       â”‚
       â–¼
Deterministic Software Implementation
       â”‚
       â–¼
Deterministic Automated Unit Tests
       â”‚
       â–¼
Versioned Provenance & Metadata
       â”‚
       â–¼
UI Visual Presentation & Scientific Interpretation
```

---

## 2. Directory Structure

```text
docs/research/
â”œâ”€â”€ README.md                     # This document: governance & research directory map
â”œâ”€â”€ SOURCE_REGISTRY.md            # Authoritative index of literature sources (R001â€“R008)
â”œâ”€â”€ THEORY_MAP.md                 # Physical acoustic chain to mathematical abstractions
â”œâ”€â”€ ALGORITHM_DECISIONS.md        # Decision records: CORE_NOW, NEXT_DSP, RESEARCH_LATER, REJECTED
â”œâ”€â”€ SCIENTIFIC_CONVENTIONS.md     # 3-representation model, sampling policies, automatic analysis
â”œâ”€â”€ MATH_CONVENTIONS.md           # Rigorous mathematical definitions and notation
â”œâ”€â”€ UNITS_AND_CALIBRATION.md      # Strict units policy (prohibition of uncalibrated Pa/dB SPL)
â”œâ”€â”€ ANALYSIS_PROFILES.md          # Versioned scientific configurations (RAW, GENERAL, PHANTOM, etc.)
â”œâ”€â”€ RESEARCH_BACKLOG.md           # Open research gaps requiring formal literature grounding
â””â”€â”€ sources/                      # Individual source dossier cards (R001â€“R008)
    â”œâ”€â”€ R001-rangayyan-biomedical-signal-analysis.md
    â”œâ”€â”€ R002-oppenheim-discrete-time-signal-processing.md
    â”œâ”€â”€ R003-heinzel-spectrum-estimation.md
    â”œâ”€â”€ R004-welch-power-spectrum-estimation.md
    â”œâ”€â”€ R005-schmidt-duration-dependent-hmm.md
    â”œâ”€â”€ R006-springer-logistic-regression-hsmm.md
    â”œâ”€â”€ R007-liu-hsmm-independent-database-evaluation.md
    â””â”€â”€ R008-rangayyan-biomedical-image-analysis.md  (LOW DIRECT RELEVANCE)
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
   An explicitly processed, filtered, or resampled representation used for a declared engineering task (e.g. 20â€“600 Hz bandpass, or 1000 Hz downsampled feature stream). Parameterized strictly via versioned `AnalysisProfile` declarations.
3. **DISPLAY SIGNAL:**
   A bounded, decimated representation ($\le 600$ points) computed via peak-preserving min/max aggregation (`decimate_aligned_traces_shared_time`) strictly used for UI visual rendering. **Display data never enters quantitative metric calculations.**

---

## 5. Contact & Maintenance

All updates to these research documents require peer-review against primary literature sources. Do not cite secondary summaries or fabricate page numbers. When a specific page number cannot be verified, cite the formal chapter and section title.
