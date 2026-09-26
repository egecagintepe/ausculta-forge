# AuscultaForge — Units, Calibration Policy & Noise Taxonomy

## 1. Strict Engineering Units Policy

AuscultaForge enforces a strict metrological policy regarding units: **Software must never report physical acoustic units ($\text{Pa}$, $\text{dB SPL}$) without a verified, documented calibrated acoustic measurement chain.**

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

### 1.2. Strictly Prohibited Units (Until Documented Physical Calibration)

The following units are **STRICTLY PROHIBITED** from all UI displays, REST payloads, and automated test outputs until a documented calibrated acoustic measurement chain is integrated:

| Prohibited Claim | Reason for Prohibition | Prerequisite for Future Support |
|---|---|---|
| **Pascals ($\text{Pa}$)** | Requires documented transducer acoustic sensitivity (e.g. $\text{dBFS/Pa}$ at $1\text{ kHz}$) and acoustic cavity transfer response. | Documented acoustic coupler + reference calibrated measurement microphone. |
| **Sound Pressure Level ($\text{dB SPL}$)** | $\text{dB SPL} \equiv 20 \log_{10}(p / 20\,\mu\text{Pa})$. Requires absolute acoustic pressure calibration. | Anechoic/soundproof chamber + sound level calibrator (94 dB / 114 dB SPL standard). |
| **Microphone Voltage ($\text{mV}$)** | The PUI DMM-4026-B-I2S-R candidate is a **digital I2S microphone** with an internal sigma-delta ASIC. An analog intermediate voltage does not exist on the PCB bus. | Only applicable if a custom analog AFE with external ADC is designed and measured. |

---

## 2. Container Bits vs. Representation Bits vs. Effective Sensor Precision

A critical architectural distinction is maintained between transport layout, digital word width, and physical sensor precision:

```text
32-bit I2S Transport Frame:
┌───────────────────────────────────────────────┬───────────────────────────┐
│ 24 Transmitted Representation Bits            │ 8 Unused / Zero-Padded    │
│ (PUI DMM-4026-B-I2S-R I2S Data Slot)          │ LSBs                      │
│ MSB                                           │ LSB                       │
└───────────────────────────────────────────────┴───────────────────────────┘
```

1. **`container_bits` ($32$):** The memory slot and transport bus word width allocated in DMA buffers.
2. **`transmitted_data_bits` / `representation_bits` ($24$):** The digital integer word width output by the microphone I2S port.
3. **`effective_sensor_precision_bits` (Unknown / Uncharacterized):**
   - Transmitting 24 bits over an I2S bus does **NOT** mean the acoustic sensor has 24 bits of effective analog resolution (ENOB).
   - Effective sensor precision is limited by acoustic diaphragm thermal noise, Brownian motion, cavity resonance, and internal ASIC converter noise.
   - For the PUI DMM-4026-B-I2S-R candidate, sensor effective precision remains uncharacterized until backed by physical measurement and datasheet review. The 24-bit representation width must never be equated with effective sensor precision.
4. **Quantization Noise Theory vs. Physical Noise:**
   - The theoretical quantization SNR formula $\text{SNR}_{\text{quant}} = 6.02 B + 1.76\text{ dB}$ is a mathematical property of ideal uniform quantization across full scale.
   - It represents a theoretical upper limit under idealized assumptions, **NOT** measured or achieved hardware noise performance. Real-world PCG noise is dominated by acoustic, motion, and sensor noise floors that sit orders of magnitude above theoretical 24-bit quantization noise.

---

## 3. Engineering Noise Taxonomy (8 Separate Categories)

AuscultaForge rejects vague aggregate "noise scores" (e.g., "Noise: 15%"). Acoustic degradation arises from distinct physical and computational mechanisms that must be diagnosed separately:

1. **Environmental / Acoustic Noise:** Ambient room acoustics, speech, HVAC air circulation, background traffic.
2. **Motion / Contact / Coupling Artifact:** Sub-acoustic friction, cable tugging, sensor shear, and variable holding force against skin/phantom ($<20\text{ Hz}$).
3. **Sensor / Electronic Noise:** Thermal Johnson noise, pre-amplifier 1/f flicker noise, and MEMS diaphragm Brownian motion.
4. **Quantization Noise:** Roundoff error from finite ADC word length ($q = \text{FS} / 2^{B-1}$).
5. **Clipping / Overload:** Severe non-linear distortion when acoustic pressure exceeds the microphone Acoustic Overload Point (AOP), flattening peaks at $\pm 1.0\text{ FS}$.
6. **Transport / Data-Integrity Error:** Dropped USB packets, sequence discontinuities, CRC check failures, DMA buffer overruns.
7. **Timing / Sample Discontinuity:** Non-uniform sampling intervals, clock jitter, sample rate switching discontinuities.
8. **DSP Transient / Artifact:** Filter startup warmup transients, IIR filter ringing near cutoff edges, spectral window leakage.

Any future diagnostic or quality report must preserve these separate categories rather than blending them into an uninterpretable composite metric.
