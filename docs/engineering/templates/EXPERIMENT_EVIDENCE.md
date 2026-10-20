# AuscultaForge — Laboratory Experiment & Bench Evidence Record Template

> **Instructions:** Use this template when logging physical laboratory measurements, hardware-in-the-loop tests, phantom acoustic experiments, or transducer comparative trials.

---

## Experiment Metadata

- **Experiment ID:** `EXP-YYYYMMDD-XX`
- **Date & Time:** `YYYY-MM-DD HH:MM UTC`
- **Location / Laboratory:** [e.g., Department Acoustics Laboratory]
- **Operators / Witnesses:** [Kaan / Ozan / Ege]
- **Module Focus:** `[Module A (Acoustics) / Module B (Embedded) / Cross-Module Integration]`
- **Status:** `[PLANNED / IN_PROGRESS / BENCH_VERIFIED / REJECTED]`

---

## 1. Objective and Hypothesis

- **Primary Goal:** *e.g., Measure frequency response and sensitivity of INMP441 MEMS microphone against ECM reference on silicone acoustic phantom.*
- **Expected Outcome:** *e.g., Coherence $\gamma_{xy}^2(f) > 0.85$ over $50\text{--}500\text{ Hz}$ band.*

---

## 2. Experimental Setup and Hardware Bill of Materials

### 2.1 Hardware Configuration
- **Transducer 1 (DUT):** INMP441 I2S MEMS breakout board (Serial / Lot ID)
- **Transducer 2 (Reference):** Calibrated reference microphone / ECM
- **Acoustic Coupling:** Custom 3D printed stethoscope bell / diaphragm
- **Phantom Material:** Silicone / Agar phantom (Dimensions, shore hardness)
- **Acoustic Excitation Source:** Audio exciter / transducer driven by function generator
- **Acquisition Host:** ESP32-S3 DevKitC-1 v1.1 connected via USB CDC-ACM to Host PC

### 2.2 Environmental Conditions
- Ambient Temperature: $XX.X^\circ\text{C}$
- Relative Humidity: $XX\%$
- Ambient Acoustic Noise Level (unweighted): $XX\text{ dB SPL}$ (if calibrated meter available)

---

## 3. Excitation Signals and Test Parameters

- **Sampling Rate:** $48\,000\text{ Hz}$
- **Stimulus Type:** `[Logarithmic Sine Sweep 20 Hz – 2 kHz / Bandlimited Pink Noise / Artificial S1-S2 Cardiac Pulse]`
- **Duration:** $XX\text{ seconds}$
- **Exciter Drive Amplitude:** $XX\text{ mV}_\text{RMS}$

---

## 4. Observed Results and Measured Data

### 4.1 Numerical Metrics

| Metric | Target / Specification | Measured ValueDUT | Measured ValueRef | Unit | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Passband Flatness (50–500 Hz)** | $\pm 3\text{ dB}$ | | | $\text{dB}$ | |
| **50 Hz Mains Interference** | $< -40\text{ dBFS}$ | | | $\text{dBFS}$ | |
| **Signal-to-Noise Ratio (SNR)** | $> 45\text{ dB}$ | | | $\text{dB}$ | |
| **System Coherence $\gamma^2(f)$** | $> 0.80$ | | | [0.0, 1.0] | |
| **Total Harmonic Distortion (THD)** | $< 1.0\%$ | | | $\%$ | |

### 4.2 Data Artifact Locations
- Raw Lossless WAV File: `data/experiments/EXP-YYYYMMDD-XX/raw_48k.wav`
- Session Metadata JSON: `data/experiments/EXP-YYYYMMDD-XX/session_meta.json`
- SHA-256 Digest: `[64-character hexadecimal SHA-256]`

---

## 5. Engineering Observations and Anomalies

- *Acoustic leakage or seal degradation during measurement:*
- *Cable microphonics or mechanical vibration transmission:*
- *Any observed USB packet loss, frame drops, or buffer underruns:*

---

## 6. Academic Significance and Defense Traceability

- **Curriculum Milestone:** EEE495 / EEE496 Laboratory Milestone #X
- **Defense Topic:** Explaining the difference between simulated phantom impedance and real human thoracic tissue.
