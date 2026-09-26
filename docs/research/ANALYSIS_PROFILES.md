# AuscultaForge — Scientific Analysis Profiles Specification

## 1. Concept & Architecture

An **Analysis Profile** in AuscultaForge is a declarative, versioned specification that defines the exact mathematical parameters, sample rate policies, filter configurations, and feature extraction pipelines applied to a discrete audio stream.

Analysis profiles enforce reproducibility across automated tests, offline laboratory replays, and UI displays:
- **No Invisible Heuristics:** Algorithms never apply hidden adaptive filters or undocumented thresholds.
- **Traceability:** Every profile cites its primary literature sources from [SOURCE_REGISTRY.md](file:///c:/Dev/Antigravity/bitirme/ausculta-forge/docs/research/SOURCE_REGISTRY.md).
- **Engineering Configurations:** Profiles are engineering configurations, **NEVER** clinical diagnostic modes.

---

## 2. Standard Profile Catalog

### 2.1. `RAW_INTEGRITY_V1`
- **Identifier:** `RAW_INTEGRITY_V1` (Version `1.0.0`)
- **Purpose:** Hardware ingestion integrity audit, packet loss detection, clipping analysis, and raw capture integrity.
- **Sample Rate Policy:** Native hardware rate ($48,000\text{ Hz}$).
- **Filter Policy:** None (All-pass bypass).
- **Spectral Policy:**
  - Window: Hann, $N_{\text{perseg}} = 2048$, $N_{\text{overlap}} = 1024$.
  - Bin Spacing: $\Delta f = 48000 / 2048 = 23.44\text{ Hz}$.
  - Detrend: None.
  - Scaling: Power Spectral Density ($\text{FS}^2/\text{Hz}$).
- **Feature Policy:** Digital clipping counter ($\ge 0\text{ dBFS}$), `container_bits = 32`, `transmitted_data_bits = 24`.
- **Literature Basis:** Oppenheim & Schafer (R002), Heinzel et al. (R003).

---

### 2.2. `GENERAL_PCG_V1`
- **Identifier:** `GENERAL_PCG_V1` (Version `1.0.0`)
- **Purpose:** Engineering live monitoring and display passband for acoustic heart sound visualization.
- **Sample Rate Policy:** Native ($48,000\text{ Hz}$) or specimen native rate.
- **Filter Policy:**
  - Prototype: 4th-order Butterworth bandpass ($20\text{--}600\text{ Hz}$).
  - Structure: Cascaded Second-Order Sections (SOS), strictly causal IIR.
- **Spectral Policy:**
  - Window: Hann, $N_{\text{perseg}} = 512$, $N_{\text{overlap}} = 256$.
  - Detrend: Constant (DC subtraction).
  - Scaling: Power Spectral Density ($\text{FS}^2/\text{Hz}$).
- **Feature Policy:** RMS, Peak, Crest Factor, Band Energy Ratios ($0\text{--}20$, $20\text{--}150$, $150\text{--}600$, $>600\text{ Hz}$).
- **Literature Basis:** Rangayyan (R001), Oppenheim & Schafer (R002), Welch (R004).

---

### 2.3. `PHANTOM_VALIDATION_V1`
- **Identifier:** `PHANTOM_VALIDATION_V1` (Version `1.0.0`)
- **Purpose:** Quantitative reference-vs-capture alignment, delay estimation, amplitude scale estimation, and coherence.
- **Sample Rate Policy:** Rational polyphase resampling (`scipy.signal.resample_poly`) to match capture to reference rate.
- **Filter Policy:** Identical matching passband applied to both channels prior to comparison.
- **Spectral Policy:**
  - Window: Hann, $N_{\text{perseg}} = 512$, $N_{\text{overlap}} = 256$, $N_{\text{fft}} = 512$.
  - Evaluation Range: $0\text{--}1000\text{ Hz}$.
  - Detrend: Constant.
- **Feature Policy:**
  - Raw cross-correlation delay estimation (ms and samples); reported NCC (centered Pearson correlation) after alignment.
  - Least-squares gain ($\hat{g}$).
  - RMSE (evaluated directly on $y_{\text{aligned}} - x_{\text{aligned}}$ without gain scaling), NRMSE (divided by $\text{RMS}(x_{\text{aligned}})$), SER (dB, capped at 100 dB).
  - Magnitude-squared coherence ($\gamma^2(f)$) with engineering PCG passband mean ($20\text{--}600\text{ Hz}$).
- **Literature Basis:** Rangayyan (R001), Oppenheim & Schafer (R002), Heinzel et al. (R003), Welch (R004).

---

### 2.4. `PCG_EVENT_FEATURES_V1`
- **Identifier:** `PCG_EVENT_FEATURES_V1` (Version `1.0.0`)
- **Purpose:** Deterministic envelope extraction for locating candidate cardiac acoustic events without heuristic black-boxes.
- **Sample Rate Policy:** Decimate to $1,000\text{ Hz}$ after anti-aliasing low-pass filtering.
- **Filter Policy:** 4th-order Butterworth bandpass ($25\text{--}400\text{ Hz}$) following Schmidt et al. (2010).
- **Spectral Policy:** Window: Hamming, $N_{\text{perseg}} = 256$, $N_{\text{overlap}} = 128$.
- **Feature Policy:**
  - Hilbert transform instantaneous amplitude envelope: $A[n] = \sqrt{x^2[n] + \mathcal{H}\{x\}^2[n]}$.
  - Homomorphic envelope via complex cepstrum log filtering.
  - Short-term sliding energy envelope ($30\text{ ms}$ window).
- **Literature Basis:** Rangayyan (R001), Schmidt et al. (R005), Springer et al. (R006).

---

### 2.5. `SPRINGER_SEGMENTATION_RESEARCH_V1`
- **Identifier:** `SPRINGER_SEGMENTATION_RESEARCH_V1` (Version `1.0.0`)
- **Purpose:** Research reproduction profile for the Springer et al. (2016) 4-feature downsampled stream for future LR-HSMM state decoding.
- **Sample Rate Policy:** Downsample audio to $1,000\text{ Hz}$; compute envelopes; downsample feature streams to $50\text{ Hz}$.
- **Filter Policy:** Polyphase anti-aliasing low-pass filter to $1,000\text{ Hz}$ (`springer_polyphase_anti_alias_1000hz`). Schmidt 25–400 Hz Butterworth is not mixed into this profile to preserve strict single-source traceability.
- **Feature Policy:** Four normalized feature envelopes at $50\text{ Hz}$:
  1. Homomorphic envelope
  2. Hilbert envelope
  3. Wavelet envelope (stationary wavelet transform level 3)
  4. Power spectral density envelope
- **Segmentation Policy:** Logistic Regression emission probabilities + Modified Viterbi duration tracking (Planned).
- **Literature Basis:** Springer et al. (R006), Liu et al. (R007).

---

## 3. Schema & Provenance Invariants

1. **JSON Serialization:**
   Every generated comparison report stores:
   ```json
   "provenance": {
     "analysis_profile_id": "PHANTOM_VALIDATION_V1",
     "analysis_profile_version": "1.0.0",
     "app_version": "1.0.0",
     "git_commit_sha": "...",
     "python_version": "...",
     "numpy_version": "...",
     "scipy_version": "..."
   }
   ```
2. **Backward Compatibility:**
   Historical reports lacking profile fields are loaded without error, gracefully reporting profile metadata as legacy / unassigned.
