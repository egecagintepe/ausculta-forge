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
  - Window: Hann, $n_{\text{perseg}} = 2048$, $n_{\text{overlap}} = 1024$.
  - Bin Spacing: $\Delta f = 48000 / 2048 = 23.44\text{ Hz}$ (discrete frequency-bin spacing, not physical resolving power).
  - Detrend: None.
  - Scaling: Power Spectral Density ($\text{FS}^2/\text{Hz}$).
- **Feature Policy:** Digital clipping counter ($\ge 0\text{ dBFS}$), `container_bits = 32`, `transmitted_data_bits = 24`.
- **Literature Basis:** Oppenheim & Schafer (R002), Heinzel et al. (R003).

---

### 2.2. `GENERAL_PCG_V1`
- **Identifier:** `GENERAL_PCG_V1` (Version `1.0.0`)
- **Purpose:** Engineering live monitoring and display passband for acoustic heart sound visualization.
- **Passband Semantics:** Provisional engineering development preset; attenuates content outside 20–600 Hz (does not eliminate noise). Content below 20 Hz is a very-low-frequency (VLF) region (drift, motion/contact artifacts, and potential legitimate mechanical content); content above 600 Hz is extended/high-frequency acoustic content (not automatically noise). Neither region is assigned pathological meaning.
- **Sample Rate Policy:** Native ($48,000\text{ Hz}$) or specimen native rate.
- **Filter Policy:**
  - Prototype: 4th-order Butterworth bandpass ($20\text{--}600\text{ Hz}$).
  - Structure: Cascaded Second-Order Sections (SOS), strictly causal IIR.
- **Spectral Policy:**
  - Window: Hann, $n_{\text{perseg}} = 512$, $n_{\text{overlap}} = 256$.
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
  - Magnitude-squared coherence ($\gamma^2(f)$) with engineering PCG passband mean ($20\text{--}600\text{ Hz}$); evaluates frequency-dependent linear association under estimator assumptions (alone does not establish causality).
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
- **Purpose:** Research reproduction profile for Springer et al. (2016) 4-feature downsampled stream for future LR-HSMM state decoding.
- **Verified R006 Pipeline:**
  - Raw PCG $\to$ polyphase anti-alias downsample to $1,000\text{ Hz}$.
  - Feature extraction at $1,000\text{ Hz}$:
    1. Homomorphic envelope
    2. Hilbert transform envelope
    3. Wavelet envelope (stationary wavelet transform level 3)
    4. Power spectral density envelope: mean PSD from $40\text{--}60\text{ Hz}$, $50\text{ ms}$ analysis window ($n_{\text{perseg}} = 50$ samples at $1,000\text{ Hz}$), $50\%$ overlap ($n_{\text{overlap}} = 25$ samples), Hamming window. No arbitrary $N_{\text{FFT}}$ is invented.
  - Per-recording feature normalization: subtract mean / divide standard deviation ($z$-score normalization).
  - Downsample feature vectors to $50\text{ Hz}$ ($20\text{ ms}$ feature cadence).
- **Filter Policy:** Polyphase anti-aliasing low-pass filter to $1,000\text{ Hz}$ (`springer_polyphase_anti_alias_1000hz`). Schmidt 25–400 Hz Butterworth is kept OUT of this strict profile to preserve verified R006 provenance.
- **Spectral Policy:**
  - Window: Hamming
  - $n_{\text{perseg}} = 50$
  - $n_{\text{overlap}} = 25$
  - $N_{\text{FFT}} = \text{None}$
  - Detrend: Constant
- **Feature Policy:**
  - `psd_envelope_band_hz`: `[40, 60]`
  - `psd_envelope_window_seconds`: `0.05`
  - `psd_envelope_overlap_fraction`: `0.5`
  - `per_recording_z_normalization`: `true`
  - `feature_sampling_rate_hz`: `50.0`
- **Segmentation Policy:** Logistic Regression emission probabilities + Modified Viterbi duration tracking (Planned Stage B).
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
