# AuscultaForge — Scientific Conventions & Architecture Invariants

## 1. Architectural Invariant: The Three Signal Representations

To prevent confusion between hardware reality, mathematical analysis, and user-interface constraints, AuscultaForge enforces an absolute separation across three signal representations:

```text
┌────────────────────────────────────────────────────────┐
│ 1. ACQUISITION SIGNAL                                  │
│ - Hardware boundary: 24 transmitted bits in 32-bit slot│
│ - Host ingestion: normalized to full-rate float32      │
│ - SessionRecorder: full-rate float32 WAV master        │
│ - Truthful: zero decimation, zero artificial smoothing │
│ - Note: Bit-exact integer archival tracked in backlog  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 2. ANALYSIS SIGNAL                                     │
│ - Explicitly processed stream for a declared task      │
│ - Resampled to task rate with anti-aliasing (e.g. 1k)  │
│ - Evaluated on full-rate arrays via pcg_core           │
│ - Never altered by browser rendering constraints       │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 3. DISPLAY SIGNAL                                      │
│ - Bounded, decimated stream (<= 600 points per window) │
│ - Peak-preserving shared-time decimation               │
│ - Strictly visualization-only in React / Canvas / SVG  │
│ - INVARIANT: NEVER becomes input to quantitative math  │
└────────────────────────────────────────────────────────┘
```

### Invariant Rules:
1. **No Metric Contamination:** Metrics (NCC, LS gain, RMSE, SER dB, PSD, coherence) are **never** calculated on display series. They are strictly evaluated on full-rate analysis arrays.
2. **Truthful Decimation Labeling:** Display decimation must never be described as acquisition decimation or sensor downsampling.
3. **Decoupled Recording:** A client dropping display frames under backpressure never causes samples to be dropped from the acquisition recording.
4. **Recording Format Precision:** The current `SessionRecorder` persists full-rate normalized `float32` WAV files. It must **NOT** be described as bit-exact integer 24-bit PCM archival until integer raw disk streaming is implemented.

---

## 2. Acquisition vs. Analysis Sample Rate Policy

### 2.1. Raw Acquisition Master (48 kHz)
Hardware Rev-A operates at:
- **Sample Rate:** $48,000\text{ samples/s}$
- **Channels:** 1 (Mono)
- **Container Word:** 32-bit signed integer slot (`container_bits = 32`)
- **Transmitted Data Bits:** 24 bits (`transmitted_data_bits = 24`, PUI DMM-4026-B-I2S-R MEMS candidate)
- **Effective Sensor Precision:** Unknown/profile-specific until backed by physical measurement and datasheet review (`effective_sensor_precision_bits` is uncharacterized).

> **Scientific Clarification on Bandwidth & Aliasing:**
> - It is **NOT** claimed that phonocardiographic heart sounds require a 24 kHz Nyquist bandwidth. Clinical PCG diagnostic information concentrates below 1000 Hz. The 48 kHz rate is a hardware standard providing generous digital oversampling.
> - High sample rate does **NOT** by itself guarantee anti-aliasing. Digital anti-aliasing is implemented for rate conversion (`scipy.signal.resample_poly`), but analog front-end anti-aliasing depends on the physical MEMS microphone internal sigma-delta ASIC filter response. Overall aliasing protection is therefore classified as `PARTIAL` until hardware bench validation occurs.

### 2.2. Task-Specific Analysis Downsampling
Downsampling for specific PCG algorithms is explicitly supported through a declared processing branch:

```text
48 kHz Raw Acquisition Master
        │
        ├── Full-Rate Normalized Host Stream (float32 SampleBlock)
        │       │
        │       ├── Full-Rate Session Recording (float32 WAV)
        │       ├── Packet Ingestion & Stream Integrity Audit
        │       └── Wideband Acoustic Phantom Validation (20–1000 Hz)
        │
        └── PCG Segmentation Research Branch
                │
                ▼ (Scipy resample_poly: rational polyphase anti-aliasing)
            1,000 Hz Downsampled Acoustic Stream
                │
                ▼ (Envelope extraction: Hilbert, Homomorphic, Wavelet, PSD)
            50 Hz Downsampled Feature Stream (Springer et al., 2016)
                │
                ▼
            LR-HSMM Viterbi State Decoding
```

---

## 3. Spectral Analysis Scientific Conventions

Exact metrological terms must be maintained without colloquial interchangeability:

| Term | Mathematical Definition | Dimensions / Units | Context in AuscultaForge |
|---|---|---|---|
| **DFT** | $X[k] = \sum_{n=0}^{N-1} x[n] e^{-j 2\pi k n / N}$ | Same as input $x[n]$ | Discrete Fourier Transform definition. |
| **FFT** | Fast $\mathcal{O}(N \log N)$ algorithm for DFT | Same as DFT | Computational implementation. |
| **Spectrum** | Magnitude complex array $\|X[k]\|$ | $\text{FS}$ or Volts | Magnitude across discrete bins. |
| **Power Spectrum** | $P[k] = \frac{1}{S_1^2} \|X[k]\|^2$ | $\text{FS}^2$ | Discrete sinusoidal component power. |
| **Power Spectral Density (PSD)** | $S_{xx}(f) = \frac{1}{f_s S_2} \langle \|X[k]\|^2 \rangle$ | $\text{FS}^2 / \text{Hz}$ | Continuous power distribution density. |
| **Linear Spectral Density (LSD)** | $\sqrt{S_{xx}(f)}$ | $\text{FS} / \sqrt{\text{Hz}}$ | Amplitude spectral density per $\sqrt{\text{Hz}}$. |
| **Spectrogram / STFT** | Time-localized windowed Fourier transform | Matrix over $(t, f)$ | Time-frequency visualization. |

### 3.1. Frequency-Bin Spacing Invariant
The discrete frequency-bin spacing is governed by the sampling rate and FFT transform length:

$$\Delta f = \frac{f_s}{N_{\text{FFT}}}$$

**Distinction Between Frequency-Bin Spacing and Spectral Resolving Power:**
Frequency-bin spacing $\Delta f = f_s / N_{\text{FFT}}$ defines the discrete frequency grid interval. It must **not** be automatically called or equated to the "minimum separable frequency resolution" or physical spectral resolving power.

Effective spectral resolution is fundamentally governed by the finite time-domain observation length ($N_{\text{samples}}$), segment/window length ($n_{\text{perseg}}$), and the window function's main-lobe width (e.g. Equivalent Noise Bandwidth and main-lobe characteristics documented in Heinzel et al., R003). Applying zero-padding ($N_{\text{FFT}} > n_{\text{perseg}}$) interpolates the underlying Discrete-Time Fourier Transform (DTFT) on a denser grid, producing closely spaced frequency samples without creating new physical resolving information.

Notation standards:
- $N_{\text{samples}}$: Total sample count in the recording or time sequence.
- $n_{\text{perseg}}$: Length of each windowed segment / analysis block (samples).
- $N_{\text{FFT}}$: FFT transform size in samples ($N_{\text{FFT}} \ge n_{\text{perseg}}$).
- $\Delta f$: Discrete frequency-bin spacing ($f_s / N_{\text{FFT}}$).

### 3.2. Block Size vs. Spectral Window Length
- **Acquisition Packet Size:** 512 samples at $48\text{ kHz}$ represents $10.67\text{ ms}$ of time, which yields a frequency-bin spacing of $\Delta f = 48000 / 512 = 93.75\text{ Hz}$.
- **Metrological Consequence:** A single 512-sample hardware packet is completely inadequate for PCG spectral analysis, where bin spacing and resolving capability of $5\text{--}10\text{ Hz}$ are required to separate fundamental cardiac frequencies.
- **Invariant:** Spectral analysis aggregates multiple hardware blocks into an appropriate rolling window ($n_{\text{perseg}} \ge 2048$ or downsampled $n_{\text{perseg}}=512$ at 4 kHz) to achieve adequate frequency-bin spacing ($\Delta f \le 8\text{ Hz}$ at 4 kHz).

---

## 4. Filter Semantics & Presets

1. **No Universal Clinical Band:** There is no single universally recognized "clinical PCG band" in medical literature. Different clinical guidelines and historical analog stethoscopes emphasize different ranges:
   - Bell Mode: $20\text{--}200\text{ Hz}$ (low-frequency gallops, third/fourth heart sounds).
   - Diaphragm Mode: $100\text{--}500\text{ Hz}$ (high-frequency murmurs, valve clicks).
   - AuscultaForge Provisional Engineering Preset: $20\text{--}600\text{ Hz}$ (`GENERAL_PCG_V1`):
     - This is a provisional engineering development preset, NOT an externally validated clinical standard or diagnostic band.
     - The 4th-order Butterworth filter attenuates content outside the development passband; it does NOT eliminate noise below 20 Hz or above 600 Hz.
     - The region below 20 Hz is a very-low-frequency (VLF) band that may contain sensor DC drift and motion/contact artifacts, AND potentially legitimate mechanical/acoustic content.
     - The region above 600 Hz is extended/high-frequency acoustic content, not automatically noise.
     - Neither region may be assigned pathological or clinical diagnostic meaning.
2. **Causal vs. Zero-Phase Filtering:**
   - **Live Streaming (`pcg_core.dsp.StreamingBandpass`):** Strictly causal IIR filtering ($y[n] = \sum b_k x[n-k] - \sum a_k y[n-k]$ via `process()`). Introduces frequency-dependent group delay.
   - **Offline Post-Processing:** If zero-phase forward-backward filtering (`sosfiltfilt`) is ever used, metadata must explicitly record `"phase_policy": "zero_phase_noncausal"`.
3. **Maximally Flat $\ne$ Zero Phase Distortion:** The Butterworth magnitude response is maximally flat in the passband with no equiripple ripple; however, its phase response is non-linear, especially near the 20 Hz and 600 Hz cutoff edges.

---

## 5. Automatic Analysis Philosophy

In AuscultaForge, **"Automatic Analysis"** strictly means **deterministic, transparent orchestration**; it never means black-box neural networks or hidden heuristic filtering.

Every automated analysis report must answer:
1. **What was done?** Exact mathematical functions invoked.
2. **Why?** Stated physical or engineering purpose.
3. **With what parameters?** Explicit filter cutoffs, window types, FFT lengths, and segment overlaps.
4. **On which signal representation?** Acquisition master vs. specific analysis downsampled stream.
5. **Using which profile?** Versioned `AnalysisProfile` identifier.
6. **Grounding source?** Citable peer-reviewed reference ID (e.g. R001, R004, R006).

---

## 6. PCG State Terminology Standards

To avoid conflating raw acoustic features with physiological truth, AuscultaForge strictly distinguishes three levels of cardiac labeling:

1. **Candidate Event:** An amplitude peak, energy envelope burst, or zero-crossing detected by a deterministic mathematical threshold (e.g. `energy_peak_candidate_3`).
2. **Segmented State:** A state inferred by a validated probabilistic model (e.g. `S1`, `SYSTOLE`, `S2`, `DIASTOLE` from an active HSMM).
3. **Reference Annotation:** A ground-truth physiological label provided by an expert physician or synchronized ECG R-peak / dicrotic notch timing in an external benchmark database (Liu et al., R007).

> **Rule:** An unvalidated acoustic burst must **NEVER** be labeled as $S_1$ or $S_2$ in production telemetry without a declared segmentation profile and evaluation confidence bounds.
