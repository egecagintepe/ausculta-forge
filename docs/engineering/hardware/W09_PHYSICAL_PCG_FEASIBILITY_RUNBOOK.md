# AuscultaForge — Week 9 Physical PCG Feasibility Runbook

**Document ID:** `AF-RUNBOOK-W09-PCG-20261118`  
**Date:** 18 November 2026  
**Module Owners & Assigned Roles:**
- **Module A (Hardware & Mechanics):** Kaan
- **Module B (Electrical & Embedded Verification):** Ozan
- **Module C (Software Orchestration & Quantitative Analysis):** Ege Çağın Tepe  
**Target Milestone:** SDP4 Week 9 Feasibility Gate (Acoustic Phantom PCG Playback & Acquisition)  
**Pass Criteria:** Clean 10-second physical acquisition matching an independently known clinical PCG recording with 0 dropped packets, 0 CRC errors, near-clipping < 0.05%, steady-state SNR > 12 dB in 20–500 Hz, normalized cross-correlation > 0.35, and visually identifiable S1/S2 heart sound morphology.

---

## 1. Role Allocation & Operational Responsibilities

To maintain strict academic traceability and experimental safety:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        EXPERIMENT ROLES & DIVISION                     │
├──────────────────┬──────────────────┬──────────────────────────────────┤
│ KAAN (Module A)  │ OZAN (Module B)  │ EGE (Module C)                   │
├──────────────────┼──────────────────┼──────────────────────────────────┤
│ • Exciter seating│ • DMM rails      │ • Software script execution      │
│ • Phantom pad    │ • PAM8403 power  │ • Stimulus generation & playback │
│ • Gel application│ • BTL isolation  │ • USB CDC ingest monitoring      │
│ • Chestpiece seal│ • Volume dial    │ • Cross-correlation & coherence  │
│ • Contact force  │ • Packet counter │ • S1/S2 envelope analysis        │
│ • Setup photos   │ • Thermal check  │ • Evidence archival & commit     │
└──────────────────┴──────────────────┴──────────────────────────────────┘
```

---

## 2. Phase-by-Phase Execution Runbook

### Phase 0: Cold Electrical Preflight & Safety Inspection

**Responsible:** Ozan (Verified by Kaan)  
**Tools:** Digital Multimeter (DMM), safety checklist from `PHANTOM_BOM_AND_WIRING_CHECKLIST.md`.

1. **Unpowered Continuity & Short-Circuit Check:**
   - Disconnect all USB cables and the PAM8403 5 V power supply.
   - Set DMM to Continuity / Resistance (Ω).
   - Check PAM8403 `OUT_L+` to `GND`: Confirm **OPEN / > 100 kΩ**.
   - Check PAM8403 `OUT_L-` to `GND`: Confirm **OPEN / > 100 kΩ**.
   - Check INMP441 `VDD` to `GND`: Confirm **No Short-Circuit (> 1 MΩ)**.
   - Check INMP441 `L/R` pin: Confirm **Connected to GND (0 Ω, Left channel)**.
2. **Powered Voltage Verification (Without Audio Drive):**
   - Connect PC USB cable to ESP32-S3 (Right connector, Native USB).
   - Measure ESP32-S3 `3V3` to `GND` rail: Confirm **3.15 V to 3.45 V** (target: 3.28 V).
   - Turn on the independent 5 V supply to the PAM8403: Measure `+5V` to `GND`: Confirm **4.8 V to 5.25 V**.
   - Verify neither the ESP32-S3 nor the PAM8403 exhibits abnormal heating.

---

### Phase 1: Mechanical Acoustic Phantom Setup

**Responsible:** Kaan (Verified by Ege)  
**Tools:** 30 mm 12 Ω exciter, silicone/gelatin phantom puck, ultrasound coupling gel, stethoscope chestpiece, 200 g contact weight.

1. **Acoustic Transducer Coupling:**
   - Place the 30 mm 12 Ω vibration exciter flat on the rigid bench surface or mounting puck.
   - Apply a small drop (~0.5 ml) of medical ultrasound transmission gel to the vibrating face of the exciter.
   - Gently press the bottom surface of the compliant phantom puck onto the exciter, ensuring no air bubbles are trapped.
2. **Stethoscope Chestpiece Coupling:**
   - Apply a thin layer of ultrasound gel to the top surface of the phantom puck.
   - Place the stethoscope chestpiece diaphragm centrally over the phantom opposite the exciter.
   - Place the 200 g calibration weight (or adjust the laboratory clamp) to exert a stable ~1.5–2.0 N contact force.
3. **Microphone Cavity Seal:**
   - Verify that the INMP441 circular breakout board is seated against the acoustic stem/cavity of the chestpiece.
   - Visually confirm the central acoustic sound hole on the underside of the INMP441 is unobstructed.
   - Seal the perimeter with a soft silicone ring or non-hardening putty to eliminate ambient room sound leakage.
4. **Photographic Evidence Collection (Kaan):**
   - Take 3 high-resolution photos:
     1. Perspective view of complete mechanical stack (exciter + phantom + chestpiece + weight).
     2. Close-up of INMP441 seating and wiring.
     3. DMM screen showing 5 V amplifier supply and 3.28 V ESP32 rail.

---

### Phase 2: Host Software Orchestration & Stimulus Calibration

**Responsible:** Ege (Module C)  
**Tools:** AuscultaForge CLI, Python 3.11 `.venv`, `tools/hardware/run_phantom_pcg_experiment.py`.

1. **Stimulus Selection:**
   - Canonical clinical heart sound recording: `data/raw/week6_real_pcg_20261026/circor/40058_AV.wav` (Aortic valve PCG, normal S1/S2 rhythm, duration 11.89 s).
   - The automation tool resamples the 4 kHz source to 48 kHz, normalizes peak amplitude to -3 dBFS (0.707 FS), and prepares the 10.0-second playback buffer.
2. **Audio Volume Setting (Low Volume Start):**
   - Set PC master output volume to **20%**.
   - Ozan stands by the PAM8403 power switch / volume pot.
3. **Execution Command:**
   ```powershell
   # Activate Python environment
   .\.venv\Scripts\Activate.ps1

   # Run automated phantom experiment
   python tools/hardware/run_phantom_pcg_experiment.py `
       --port COM8 `
       --reference data/raw/week6_real_pcg_20261026/circor/40058_AV.wav `
       --play-audio `
       --operator "Kaan_Ozan_Ege" `
       --notes "Trial 01 - CirCor 40058_AV through acoustic phantom with ultrasound gel"
   ```
4. **Operational Flow during Execution:**
   - The script connects to the ESP32-S3 over USB CDC.
   - Playback starts through the PC audio output into the PAM8403.
   - Concurrently, the ESP32-S3 streams 480,000 samples (10.0 s) of live INMP441 audio over USB.
   - Acquisition finishes automatically; the session WAV and telemetry JSON are saved.

---

### Phase 3: Immediate Ingest & Quality Gating

**Responsible:** Ozan & Ege  
The automated script immediately evaluates the raw capture against mandatory acceptance rules:

1. **Packet Continuity Gate:**
   - `in_stream_dropped_samples` == 0.
   - `crc_failures` == 0.
   - `sequence_discontinuities` == 0.
   - *If any packet is dropped, check USB cable and re-run.*
2. **Dynamic Range & Clipping Gate:**
   - `near_clipping_fraction` (< -0.5 dBFS or > 0.98 FS): Must be **< 0.05%** (fewer than 240 samples out of 480,000).
   - Peak amplitude: Must not saturate hard ceiling (`|x| < 0.999`).
   - *If clipping is detected, reduce PC audio volume by 5% and re-run.*
3. **Acoustic Transduction SNR Gate:**
   - Steady-state RMS signal level must exceed quiescent room noise floor by **> 12 dB** in the 20–500 Hz cardiac passband.
   - *If SNR < 12 dB, check exciter contact, gel coverage, and amplifier volume.*

---

### Phase 4: S1/S2 Morphological Similarity & Quantitative Alignment

**Responsible:** Ege (Module C)  
The script computes the mathematical similarity between the source PCG and the captured acoustic signal:

1. **Time-Domain Delay & Normalized Cross-Correlation (NCC):**
   - The script evaluates cross-correlation $R_{xy}(\tau)$ and extracts the peak lag $\tau_{opt}$.
   - **Target:** Normalized cross-correlation $NCC \ge 0.35$ through the physical acoustic channel.
2. **Passband Coherence:**
   - Welch magnitude-squared coherence $\gamma_{xy}^2(f)$ is computed across 20–500 Hz.
   - **Target:** Mean coherence in the primary 20–250 Hz cardiac passband $\ge 0.40$.
3. **S1 and S2 Envelope Peak Identification:**
   - The script extracts the Shannon energy envelope $E_s(t) = -x(t)^2 \log(x(t)^2)$ and Hilbert amplitude envelope.
   - Detects S1 (mitral/tricuspid closure) and S2 (aortic/pulmonic closure) peaks.
   - Verifies that systolic ($S_1 \to S_2$) and diastolic ($S_2 \to S_1$) intervals match the source recording rhythm (~0.6–1.0 s cardiac period).

---

## 3. Explicit STOP & Troubleshooting Criteria

| Symptom / Failure | Root Cause | Immediate Action | Operator Role |
|---|---|---|---|
| **Digital Saturation / Clipping (`near_clipping_fraction > 0.1%`)** | PC line-out volume too high or exciter driven into non-linear excursion. | Reduce PC volume from 20% to 12–15%. Repeat trial. | Ozan & Ege |
| **Low SNR / Signal Inaudible (`SNR < 6 dB`)** | Dry contact surface, trapped air bubbles, or PAM8403 5 V supply off. | Verify 5 V rail on PAM8403. Re-apply ultrasound gel. Check 3.5 mm AUX cable connection. | Kaan & Ozan |
| **Severe 50 Hz Hum / Mains Noise** | Ground loop between PC power supply and PAM8403, or unshielded audio lead. | Ensure PAM8403 is powered from a floating battery power bank. Check audio shield grounding. | Ozan |
| **Poor Cross-Correlation (`NCC < 0.20`) / Distorted Waveform** | Chestpiece diaphragm vibrating loosely or acoustic port partially obstructed. | Inspect INMP441 underside acoustic hole. Verify 200 g contact weight is centered without tilting. | Kaan |
| **USB CDC Disconnect / Port Reset** | High transient current on USB rail, or loose USB-C cable. | Verify PAM8403 is NOT powered from ESP32. Reseat USB cable into Native CDC port. | Ozan |

---

## 4. Evidence Packaging & Archival

Upon achieving a successful trial:

1. **Verify Generated Evidence Package:**
   - `experiments/phantom/trial_<timestamp>/`:
     - `session_<id>.wav`: Raw 48 kHz float32 captured audio.
     - `session_<id>.json`: Canonical session telemetry and hardware manifest.
     - `phantom_pcg_experiment_report.json`: Machine-readable similarity metrics, coherence, and delay decomposition.
     - `phantom_pcg_experiment_report.md`: Formatted academic markdown summary.
2. **Photographs Archival:**
   - Place bench photos in `experiments/phantom/trial_<timestamp>/photos/`.
   - Compute SHA-256 hashes of all photos and record them in the manifest.
3. **Git Commit & Academic Reporting:**
   - Stage report JSON and Markdown files (`git add experiments/phantom/trial_*/*.json experiments/phantom/trial_*/*.md`).
   - Leave raw WAV and high-res photos gitignored to preserve clean repository history.
   - Link trial results in `docs/sdp/week-09/submissions/` under Module A, B, and C weekly summaries.
