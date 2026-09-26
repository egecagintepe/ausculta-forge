# R003 — Heinzel et al. (2002): Spectrum and Spectral Density Estimation

## 1. Bibliographic Reference
- **Authors:** Gerhard Heinzel, Albrecht Rüdiger, Roland Schilling.
- **Title:** *Spectrum and spectral density estimation by the Discrete Fourier transform (DFT), including a comprehensive list of window functions and some new flat-top windows*.
- **Institution:** Max-Planck-Institut für Gravitationsphysik (Albert-Einstein-Institut), Teilinstitut Hannover.
- **Report Number:** Technical Report MPI-186, February 2002.
- **Authority Level:** **METROLOGY CANON FOR POWER SPECTRAL DENSITY**.

---

## 2. Scope & Application to AuscultaForge
R003 is the primary metrological authority for the mathematical scaling, window normalization, and bandwidth calculations implemented in `pcg_core.scientific_config.SpectralAnalysisConfig`.

### Key Technical Sections:
- **Section 3: The Discrete Fourier Transform and Discrete Time Series:** Discrete time scaling, sampling frequency $f_s$, and discrete frequency-bin spacing $\Delta f = f_s / N_{\text{FFT}}$ (noting that bin spacing is not physical spectral resolving power, which depends on window length and main-lobe characteristics).
- **Section 4: Window Functions and Normalization:**
  - Coherent Gain (Linear Gain): $S_1 = \sum_{n=0}^{N-1} w[n]$.
  - Noise Power Gain: $S_2 = \sum_{n=0}^{N-1} w^2[n]$.
- **Section 5: Power Spectrum vs. Power Spectral Density:**
  - Power Spectrum (PS): Scaled to preserve total discrete sinusoidal power: $P[k] = \frac{2}{S_1^2} |X[k]|^2$.
  - Power Spectral Density (PSD): Scaled to represent continuous power per Hertz: $S_{xx}[k] = \frac{2}{f_s S_2} |X[k]|^2$.
- **Section 7: Equivalent Noise Bandwidth (ENBW):**
  $$\text{ENBW} = f_s \cdot \frac{S_2}{S_1^2}$$
  Relates spectral density to discrete bin power.
- **Section 8: Preprocessing & Detrending:** Removing DC offset ($w[n] \cdot (x[n] - \bar{x})$) to prevent low-frequency spectral leakage across the primary analysis band.

---

## 3. Key Metrological Rules Enforced in AuscultaForge
1. **Explicit Scaling Declaration:**
   - Whenever a spectrum is computed or plotted, the software must explicitly declare whether it is **Power Spectral Density** ($\text{FS}^2/\text{Hz}$, default) or **Power Spectrum** ($\text{FS}^2$).
2. **Deterministic ENBW Computation:**
   - `SpectralAnalysisConfig.enbw(fs)` computes the exact Equivalent Noise Bandwidth directly from the window array coefficients:
     - Hann window: $\text{ENBW} \approx 1.50 \cdot \Delta f$.
     - Rectangular (boxcar) window: $\text{ENBW} = 1.00 \cdot \Delta f$.
     - Hamming window: $\text{ENBW} \approx 1.36 \cdot \Delta f$.
3. **Mandatory DC Subtraction (Detrending):**
   - High DC offsets from digital MEMS microphones or ADC word alignment leak into adjacent low-frequency bins (0–20 Hz) due to window side-lobes. Constant detrending (`DetrendMode.CONSTANT`) is applied by default.
