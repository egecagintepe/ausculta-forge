# AuscultaForge — Physical Signal Chain to Theory Map

## 1. Physical Propagation Chain

AuscultaForge evaluates acoustic signal transmission through a controlled laboratory chain:

```text
┌───────────────────────────┐
│ Known Digital Reference   │  x[n] (Normalized full-scale digital waveform)
│ x[n]                      │
└─────────────┬─────────────┘
              │ DAC & Power Amplifier
              ▼
┌───────────────────────────┐
│ Playback Transducer       │  Electro-acoustic conversion (Exciter / Speaker)
│ (Actuator / Loudspeaker)  │
└─────────────┬─────────────┘
              │ Acoustic pressure wave p_in(t)
              ▼
┌───────────────────────────┐
│ Acoustic Phantom Medium   │  Viscoelastic tissue-mimicking material (Silicone / Gel)
│ (Acoustic Path)           │  Frequency-dependent acoustic attenuation & dispersion
└─────────────┬─────────────┘
              │ Acoustic pressure wave p_out(t)
              ▼
┌───────────────────────────┐
│ Mechanical / Acoustic     │  Contact force, skin-cup acoustic seal,
│ Coupling Interface        │  entrapped air cavity acoustic compliance
└─────────────┬─────────────┘
              │ Transduced cavity acoustic pressure
              ▼
┌───────────────────────────┐
│ Stethoscope Chestpiece    │  Acoustic bell/diaphragm resonance & chamber response
└─────────────┬─────────────┘
              │ Sound wave incident on MEMS port
              ▼
┌───────────────────────────┐
│ PUI MEMS Microphone       │  Mechanical diaphragm deflection -> capacitance change
│ (DMM-4026-B-I2S-R)        │  -> internal sigma-delta ASIC -> 24-bit I2S PCM
└─────────────┬─────────────┘
              │ I2S Digital Bus (48 kHz, 32-bit slot, 24 meaningful bits)
              ▼
┌───────────────────────────┐
│ ESP32-S3 Microcontroller  │  DMA buffer ingestion -> semantic packet formation
└─────────────┬─────────────┘
              │ USB CDC / Serial Packet Transmission
              ▼
┌───────────────────────────┐
│ Captured Signal y[n]      │  Host acquisition session (raw.wav + session.json)
└───────────────────────────┘
```

---

## 2. Mathematical System Model & Assumptions

### 2.1. Initial Engineering Linear Time-Invariant (LTI) Approximation
As an engineering first-order baseline (Oppenheim & Schafer, R002), the end-to-end channel between the known digital excitation $x[n]$ and the captured digital output $y[n]$ is modeled as a discrete-time convolution plus additive noise:

$$y[n] = (x * h)[n] + v[n] = \sum_{k=-\infty}^{\infty} x[k] h[n - k] + v[n]$$

In the frequency domain:

$$Y(f) = H(f) X(f) + V(f)$$

where:
- $x[n]$: Known discrete-time reference excitation / stimulus.
- $h[n]$: Composite discrete-time impulse response of the complete physical chain.
- $H(f)$: Complex-valued Frequency Response Function (FRF).
- $v[n]$: Additive disturbance (ambient acoustic noise, electronic thermal noise, ADC quantization noise).
- $y[n]$: Digitized captured output.

### 2.2. Critical Scientific Caveats & Physical Validity Limits

The LTI formulation above is an **engineering approximation**, NOT a proven physical identity:

1. **Nonlinearities:**
   - Playback loudspeakers exhibit harmonic distortion and voice-coil heating at higher drive levels.
   - Viscoelastic phantom polymers exhibit non-Hookean stress-strain behavior under high acoustic displacement.
   - MEMS microphone diaphragms experience mechanical compliance non-linearities near clipping limits.
2. **Time-Varying Coupling:**
   - The mechanical contact force between the stethoscope chestpiece and the phantom surface directly alters the acoustic boundary impedance.
   - Micro-slippage or variation in holding pressure produces substantial low-frequency modulation and baseline wander.
3. **No Physical Transfer Function Claims:**
   - The ratio $\hat{H}(f) = Y(f) / X(f)$ must **NEVER** be reported as a calibrated physical transfer function of the stethoscope until the loudspeaker and phantom transfer functions are independently characterized with a laboratory reference microphone.
   - AuscultaForge strictly labels current results as **Reference vs Capture Engineering Comparison**, not absolute sensor frequency calibration.

---

## 3. Metrological Policy on Frequency Response Estimators ($H_1, H_2$)

In classical experimental modal analysis and system identification:
- **$H_1(f) = \frac{S_{xy}(f)}{S_{xx}(f)}$:** Minimizes error due to noise at the output ($v[n]$).
- **$H_2(f) = \frac{S_{yy}(f)}{S_{yx}(f)}$:** Minimizes error due to noise at the input.

**Architectural Decision:**
$H_1$ and $H_2$ estimators are **NOT** implemented in the current codebase. Implementing them without an explicit random-data / white-noise excitation protocol and a calibrated acoustic impedance standard would produce misleading transfer function curves. They remain classified as `RESEARCH_LATER` pending formal grounding in a system-identification reference (Bendat & Piersol, 2010).

---

## 4. Current Operational Metrics & Model Mapping

Instead of asserting an uncalibrated $H(f)$, AuscultaForge currently implements robust, non-parametric engineering metrics:

| Physical Effect | Mathematical Model | Implementation | Source Trace |
|---|---|---|---|
| **Bulk Propagation Delay** | $y[n] \approx g \cdot x[n - D] + v[n]$ | $\arg\max_m R_{yx}[m]$ (`estimate_delay_and_align`) | Oppenheim (R002), Rangayyan (R001) |
| **Linear Scale Attenuation** | $\min_g \|y_{\text{aligned}}[n] - g \cdot x_{\text{aligned}}[n]\|^2$ | $\hat{g} = \frac{\sum x[n] y[n]}{\sum x[n]^2}$ (`compute_least_squares_gain`) | Linear Regression / LS Metrology |
| **Acoustic Residual Energy** | $e[n] = y_{\text{aligned}}[n] - x_{\text{aligned}}[n]$ | $\text{RMSE}, \text{NRMSE}, \text{SER (dB)}$ (`validate_signals`) | Rangayyan (R001), Oppenheim (R002) |
| **Spectral Energy Profile** | $S_{xx}(f) = \frac{1}{f_s S_2} \langle \|\text{FFT}\{w \cdot x\}\|^2 \rangle$ | Welch Averaged Periodogram (`compute_spectral_frame`) | Welch (R004), Heinzel (R003) |
| **Frequency-Dependent Linear Association** | $\gamma_{xy}^2(f) = \frac{\|S_{xy}(f)\|^2}{S_{xx}(f) S_{yy}(f)}$ | Magnitude-Squared Coherence (`scipy.signal.coherence`) (Note: alone does not establish causality) | Oppenheim (R002), Rangayyan (R001) |
