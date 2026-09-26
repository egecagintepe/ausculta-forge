# AuscultaForge — Units, Calibration Policy & Noise Taxonomy

## 1. Strict Engineering Units Policy

AuscultaForge enforces a strict metrological policy regarding units: **Software must never report physical acoustic units ($\text{Pa}$, $\text{dB SPL}$) without a verified, calibrated measurement chain.**

### 1.1. Permitted Engineering Units

| Permitted Unit | Symbol / Format | Physical Meaning | Software Usage |
|---|---|---|---|
| **Raw PCM Integer Code** | `raw_pcm_code` | Raw signed integer word directly from the I2S bus. | Driver ingestion, byte dumps, bit-depth integrity tests. |
| **Normalized Full Scale** | `normalized_fs` | Dimensionless float $\in [-1.0, +1.0]$ where $\pm 1.0$ is the digital clipping ceiling. | Standard DSP pipeline, filters, waveforms, audio engine. |
| **Full Scale Squared per Hz** | $\text{FS}^2/\text{Hz}$ | Non-parametric power spectral density normalized to digital full scale. | Welch PSD plots, spectral profiles. |
| **Decibels Full Scale** | $\text{dBFS}$ | $20 \log_{10}(|x| / 1.0)$ or $10 \log_{10}(P / 1.0)$. Peak is $0\text{ dBFS}$. | Spectral plots, amplitude meters, dynamic range telemetry. |
| **Relative Decibels** | $\text{dB}$ | Relative power ratio: $10 \log_{10}(P_1 / P_2)$ or SER. | Signal-to-Error Ratio (SER), gain ratio comparisons. |
| **Dimensionless Ratio** | `dimensionless` | Correlation coefficient, gain factor, crest factor, coherence $\gamma^2(f)$. | NCC, Least-Squares Gain ($g$), Mean Coherence. |

---

### 1.2. Strictly Prohibited Units (Until Physical Calibration)

The following units are **STRICTLY PROHIBITED** from all UI displays, REST payloads, and automated test outputs until calibrated laboratory acoustic equipment is integrated:

| Prohibited Claim | Reason for Prohibition | Prerequisite for Future Support |
|---|---|---|
| **Pascals ($\text{Pa}$)** | Requires certified transducer acoustic sensitivity (e.g. $-26\text{ dBFS/Pa}$ at $1\text{ kHz}$) and acoustic cavity frequency response. | Calibrated acoustic coupler + reference laboratory microphone. |
| **Sound Pressure Level ($\text{dB SPL}$)** | $\text{dB SPL} \equiv 20 \log_{10}(p / 20\,\mu\text{Pa})$. Requires absolute acoustic calibration. | Anechoic/soundproof chamber + sound level calibrator (94 dB / 114 dB SPL). |
| **Microphone Voltage ($\text{mV}$)** | The PUI DMM-4026-B-I2S-R is a **digital I2S microphone** with an integrated internal ASIC. An analog intermediate voltage does not exist on the PCB bus. | Only applicable if a custom analog AFE with external ADC is designed. |

---

## 2. Container Bits vs. Meaningful Bits

A critical distinction must be maintained between memory layout and sensor resolution:

```text
32-bit I2S Transport Frame:
┌───────────────────────────────────────────────┬───────────────────────────┐
│ 24 Meaningful Sensor Bits                     │ 8 Unused / Zero-Padded    │
│ (PUI DMM-4026-B-I2S-R Sigma-Delta Converter)  │ LSBs                      │
│ MSB                                           │ LSB                       │
└───────────────────────────────────────────────┴───────────────────────────┘
```

1. **No False Analog Resolution:** A 24-bit meaningful sample inside a 32-bit container must **NEVER** be presented as a 32-bit analog converter.
2. **Noise Floor Limits:** The theoretical SNR of a 24-bit converter is $6.02 \times 24 + 1.76 \approx 146\text{ dB}$; however, the physical MEMS acoustic sensor has an acoustic SNR of approximately $64\text{ dBA}$ (equivalent input noise $\approx 30\text{ dB SPL}$). The lowest 10–12 bits of the 24-bit word reflect ambient acoustic and thermal noise, NOT 24 bits of clean physiological data.

---

## 3. Engineering Noise Taxonomy

AuscultaForge rejects vague aggregate "noise scores" (e.g., "Noise: 15%"). Acoustic degradation arises from distinct physical mechanisms that must be diagnosed separately:

```text
                               AuscultaForge Noise Taxonomy
                                             │
      ┌───────────────────┬──────────────────┼──────────────────┬──────────────────┐
      ▼                   ▼                  ▼                  ▼                  ▼
Environmental       Motion / Contact      Sensor / Circuit    Quantization &      Transport &
Acoustic Noise      Artifacts             Electronic Noise    Clipping            Data Discontinuities
- Ambient speech    - Sensor rub         - MEMS thermal      - Digital clipping  - USB packet drops
- Room HVAC hum     - Cable tugging        Brownian noise      at 0 dBFS         - DMA sequence gaps
- Powerline 50/60Hz - Variable chest     - Preamp Johnson    - ADC word          - Buffer overrun
  electromagnetic     holding force        noise               truncation          overflows
```

### Classification Guidelines:
1. **Environmental / Acoustic Noise:** Broadband sound passing through the air or chestpiece backing. Characterized by high-frequency spectral components above 500 Hz or stationary line peaks (50/60 Hz mains).
2. **Motion / Contact Artifact:** Sub-acoustic, large-amplitude baseline wander (<20 Hz) caused by friction between the bell rim and the skin/phantom surface.
3. **Sensor / Electronic Thermal Noise:** Gaussian white-noise floor inherent to the MEMS diaphragm and integrated charge pump.
4. **Clipping / Overload:** Severe non-linear distortion when acoustic pressure exceeds the microphone Acoustic Overload Point (AOP, ~120 dB SPL), producing flattened peak plateaus at $\pm 1.0\text{ FS}$.
5. **Transport & Data Integrity Discontinuities:** Packet sequence gaps, USB endpoint stalls, or DMA buffer overruns that introduce sharp mathematical discontinuities ($\Delta y \gg 0$) into the discrete sequence.
