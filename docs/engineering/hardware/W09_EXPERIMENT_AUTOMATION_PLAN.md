# AuscultaForge — Week 9 Experiment Automation Plan

**Document ID:** `AF-PLAN-W09-AUTO-20261118`  
**Date:** 18 November 2026  
**Module Owner:** Module C (Computer Application & Quality Assessment — Ege Çağın Tepe)  
**Collaborators:** Module A (Kaan) & Module B (Ozan)  
**Implementation Tool:** `tools/hardware/run_phantom_pcg_experiment.py`  
**Target Milestone:** SDP4 Week 9 Feasibility Gate

---

## 1. Automation Rationale & Engineering Objectives

In accordance with course regulations (`SDP_Assessment_Criteria_for_Students.docx`):
> *"Results are produced by a script, not typed into a table by hand. A number that cannot be reproduced does not count as a result."*

Manual playback and separate manual recording introduce human timing jitter, inconsistent sound volume, uncalibrated gain scaling, and arbitrary visual interpretation. The AuscultaForge automated feasibility workflow solves this by executing playback, acquisition, ingest gating, signal alignment, spectral analysis, and report generation in a single deterministic script.

---

## 2. End-to-End Automated Pipeline Architecture

```
                  ┌──────────────────────────────────────────────┐
                  │ 1. REFERENCE PCG SELECTION & STIMULUS PREP   │
                  │ - CirCor DigiScope (40058_AV.wav, 4 kHz)     │
                  │ - Rational polyphase resample to 48 kHz      │
                  │ - Peak normalize to -3 dBFS (0.707 FS)       │
                  │ - Export playback WAV: stimulus_48k.wav      │
                  └──────────────────────┬───────────────────────┘
                                         │
                  ┌──────────────────────▼───────────────────────┐
                  │ 2. DUAL-THREAD SYNCHRONIZED EXECUTION        │
                  │ ┌─────────────────────────┬────────────────┐ │
                  │ │ Thread A: Audio Out     │ Thread B: USB  │ │
                  │ │ winsound.PlaySound      │ CDC Streaming  │ │
                  │ │ (48 kHz to PAM8403)     │ (480k samples) │ │
                  │ └─────────────────────────┴────────────────┘ │
                  └──────────────────────┬───────────────────────┘
                                         │
                  ┌──────────────────────▼───────────────────────┐
                  │ 3. IMMEDIATE INGEST & INTEGRITY GATING       │
                  │ - Sequence continuity check (0 dropped pkts) │
                  │ - CRC integrity check (0 CRC failures)       │
                  │ - Near-clipping fraction (< 0.05% @ >0.98 FS)│
                  │ - Quiescent vs Stimulus SNR (> 12 dB)        │
                  └──────────────────────┬───────────────────────┘
                                         │
                  ┌──────────────────────▼───────────────────────┐
                  │ 4. QUANTITATIVE ALIGNMENT & SYSTEM ID        │
                  │ - 20–500 Hz Butterworth bandpass filtering   │
                  │ - Cross-correlation time delay estimation    │
                  │ - Normalized Cross-Correlation (NCC >= 0.35) │
                  │ - Welch magnitude-squared coherence (20-250) │
                  │ - Least-squares gain & RMS ratio             │
                  └──────────────────────┬───────────────────────┘
                                         │
                  ┌──────────────────────▼───────────────────────┐
                  │ 5. S1/S2 MORPHOLOGY & ENVELOPE ANALYSIS      │
                  │ - Shannon energy envelope computation        │
                  │ - S1 and S2 systolic/diastolic peak finding  │
                  │ - Cardiac cycle period estimation (0.6–1.0 s)│
                  └──────────────────────┬───────────────────────┘
                                         │
                  ┌──────────────────────▼───────────────────────┐
                  │ 6. AUTOMATED REPORTING & PROVENANCE          │
                  │ - phantom_pcg_experiment_report.json         │
                  │ - phantom_pcg_experiment_report.md           │
                  │ - Gating status banner (PASS / PENDING)      │
                  └──────────────────────────────────────────────┘
```

---

## 3. Mathematical Foundations of Comparison Metrics

### 3.1 Delay Estimation & Cross-Correlation
Given reference stimulus $x[n]$ and captured signal $y[n]$ sampled at $f_s = 48\,000\text{ Hz}$:
$$R_{xy}[k] = \sum_{n} y[n] x[n - k]$$
The optimal sample delay $k_{opt} = \arg\max_k R_{xy}[k]$, with time lag $\tau = k_{opt} / f_s$ in seconds.

The **Normalized Cross-Correlation (NCC)** over the overlapping segment of length $N$:
$$\text{NCC} = \frac{\sum_{n=0}^{N-1} (x[n] - \bar{x})(y[n + k_{opt}] - \bar{y})}{\sqrt{\sum_{n=0}^{N-1} (x[n] - \bar{x})^2 \sum_{n=0}^{N-1} (y[n + k_{opt}] - \bar{y})^2}}$$
- $\text{NCC} \ge 0.35$: Confirms preserved cardiac sound morphology through the acoustic phantom.
- $\text{NCC} < 0.20$: Indicates signal corruption, severe acoustic reverberation, or mechanical decoupling.

### 3.2 Welch Magnitude-Squared Coherence
To assess linear system transfer fidelity across frequency:
$$\gamma_{xy}^2(f) = \frac{|P_{xy}(f)|^2}{P_{xx}(f) P_{yy}(f)}$$
where $P_{xx}(f)$ and $P_{yy}(f)$ are the auto-spectral densities and $P_{xy}(f)$ is the cross-spectral density estimated via Welch's averaged periodogram method (Hanning window, 50% overlap).
- Coherence $\gamma_{xy}^2(f) \to 1.0$ indicates an ideal linear acoustic transfer channel.
- In the primary 20–250 Hz cardiac passband, mean coherence $\ge 0.40$ demonstrates linear phonocardiogram transmission through the phantom.

### 3.3 Shannon Energy Envelope for S1/S2 Peak Identification
To extract heart sound bursts independent of high-frequency noise spikes, the normalized Shannon energy envelope is computed:
$$E_s[n] = -x_{norm}[n]^2 \log_e\left(x_{norm}[n]^2 + \epsilon\right)$$
where $x_{norm}[n] = x[n] / \max(|x[n]|)$. The envelope is smoothed with a 50 ms zero-phase moving average filter.
- Local peaks identify the alternating **S1 (systole onset)** and **S2 (diastole onset)** heart sound complexes.
- Peak-to-peak interval timing is verified against canonical cardiac physiology (heart rate 60–100 bpm, cycle duration 0.6–1.0 s).

---

## 4. Dual-Mode Execution: Physical Hardware vs. Deterministic Simulation

To ensure robust testability and CI support:

1. **Physical Hardware Mode (`--port COMx`):**
   - Connects to physical ESP32-S3 over native USB CDC.
   - Triggers asynchronous audio playback of the reference PCG through the default Windows audio output into the PAM8403.
   - Concurrently captures 480,000 samples (10.0 s @ 48 kHz) from the INMP441.
   - Evaluates real physical acoustic transfer characteristics.
   - Status: `PHYSICAL_VERIFIED` or `PHYSICAL_INCONCLUSIVE`.

2. **Deterministic Simulation Mode (`--simulate`):**
   - Requires no physical hardware.
   - Simulates acoustic propagation delay (~12.5 ms), acoustic tissue low-pass damping (~350 Hz cutoff), and gentle Gaussian noise floor.
   - Verifies the software DSP, cross-correlation, envelope extraction, and reporting pipelines in < 2 seconds.
   - Status: `SIMULATED_BENCH_TEST (PHYSICAL_GATE_PENDING)`.
   - Never mislabeled as physical hardware validation.

---

## 5. Automated Acceptance Rules (The Week 9 Gate)

| Metric | Threshold / Target | Rule Enforcement |
|---|---|---|
| **USB Data Integrity** | `dropped_samples == 0`, `crc_failures == 0` | Mandatory PASS. Any dropped sample aborts the run. |
| **Clipping Fraction** | `near_clipping_fraction < 0.05%` (|x| > 0.98 FS) | Mandatory PASS. Prevents distorted measurements. |
| **Acoustic Transduction SNR** | `steady_state_snr_20_500hz >= 12.0 dB` | Confirms sound transmission through phantom above ambient noise. |
| **Normalized Cross-Correlation** | `NCC >= 0.35` (target >= 0.45) | Confirms waveform fidelity through phantom channel. |
| **S1/S2 Heart Sound Peaks** | Identifiable alternating S1/S2 peak intervals (~0.6–1.0 s) | Confirms clinical auscultatory feature preservation. |
| **Overall Week 9 Gate** | **ALL OF THE ABOVE SATISFIED ON PHYSICAL HARDWARE** | Official Milestone Status: **PASSED**. |
