# AuscultaForge — Scientific Conventions & Architecture Invariants

## 1. Architectural Invariant: The Three Signal Representations

To prevent confusion between hardware reality, mathematical analysis, and user-interface constraints, AuscultaForge enforces an absolute separation across three signal representations:

```text
┌────────────────────────────────────────────────────────┐
│ 1. ACQUISITION SIGNAL                                  │
│ - Bit-exact digital master stream from ADC / I2S       │
│ - Hardware Rev-A: 48 kHz, mono, 24 meaningful bits     │
│ - Direct input to SessionRecorder (raw.wav)            │
│ - Truthful: zero decimation, zero artificial smoothing │
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

---

## 2. Acquisition vs. Analysis Sample Rate Policy

### 2.1. Raw Acquisition Master (48 kHz)
Hardware Rev-A operates at:
- **Sample Rate:** $48,000\text{ samples/s}$
- **Channels:** 1 (Mono)
- **Container:** 32-bit signed integer slot
- **Meaningful Data:** 24 bits (PUI DMM-4026-B-I2S-R MEMS microphone)

> **Scientific Clarification:** It is **NOT** claimed that phonocardiographic heart sounds require a 24 kHz Nyquist bandwidth. Clinical PCG diagnostic information concentrates below 1000 Hz. The 48 kHz rate is a hardware standard providing generous oversampling, eliminating analog anti-aliasing filter phase distortion, and enabling wideband phantom acoustic characterization.

### 2.2. Task-Specific Analysis Downsampling
Downsampling for specific PCG algorithms is explicitly supported through a declared processing branch:

```text
48 kHz Raw Acquisition Master
        │
        ├── Full-Rate Raw Session Recording (raw.wav)
        ├── Packet Ingestion & Stream Integrity Audit
        ├── Wideband Acoustic Phantom Validation (20–1000 Hz)
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

### 3.1. Frequency Bin Spacing Invariant
The discrete frequency bin spacing is governed solely by the FFT length:

$$\Delta f = \frac{f_s}{N_{\text{fft}}}$$

### 3.2. Block Size vs. Spectral Window Length
- **Acquisition Packet Size:** 512 samples at $48\text{ kHz}$ represents $10.67\text{ ms}$ of time, which yields $\Delta f = 48000 / 512 = 93.75\text{ Hz}$.
- **Metrological Consequence:** A single 512-sample hardware packet is completely inadequate for PCG spectral analysis, where resolution of $5\text{--}10\text{ Hz}$ is required to separate fundamental cardiac frequencies.
- **Invariant:** Spectral analysis aggregates multiple hardware blocks into an appropriate rolling window ($N \ge 2048$ or downsampled $N=512$ at 4 kHz) to achieve adequate frequency resolution ($\Delta f \le 8\text{ Hz}$).

---

## 4. Filter Semantics & Presets

1. **No Universal Clinical Band:** There is no single universally recognized "clinical PCG band" in medical literature. Different clinical guidelines and historical analog stethoscopes emphasize different ranges:
   - Bell Mode: $20\text{--}200\text{ Hz}$ (low-frequency gallops, third/fourth heart sounds).
   - Diaphragm Mode: $100\text{--}500\text{ Hz}$ (high-frequency murmurs, valve clicks).
   - AuscultaForge Engineering Preset: $20\text{--}600\text{ Hz}$ (broad development passband).
2. **Causal vs. Zero-Phase Filtering:**
   - **Live Streaming (`pcg_core.dsp.StreamingBandpass`):** Strictly causal IIR filtering ($y[n] = \sum b_k x[n-k] - \sum a_k y[n-k]$). Introduces frequency-dependent group delay.
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
