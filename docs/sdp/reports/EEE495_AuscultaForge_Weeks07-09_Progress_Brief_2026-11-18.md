# EEE 495 — Senior Design Project: AuscultaForge
## Weekly Academic Progress Brief (Weeks 7–9)

- **Date:** 18 November 2026
- **Project Title:** AuscultaForge — Digital Stethoscope Characterisation and Acquisition Platform
- **Team Members:**
  - Kaan (Module A: Acquisition Hardware and Characterisation)
  - Ozan (Module B: Embedded Acquisition and Data Path)
  - Ege Çağın Tepe (Module C: Computer Application and Quality Assessment)
- **Target Audience:** Course Instructor & Academic Advisors

---

### 1. Weekly Progress Matrix (Weeks 7–9)

| Week | Module | Planned Work (Syllabus) | Verified Progress | Outstanding Work / Next Action |
|---|---|---|---|---|
| **W07**<br>*(2–8 Nov)* | **A (Kaan)** | Build acoustic phantom (exciter + silicone layer + chestpiece). | Hardware specification and procurement research completed. Physical build paused during university midterm exam period. | Assemble physical exciter, PAM8403, and phantom block once components are on bench. |
| | **B (Ozan)** | Implement device status reporting and packet loss detection. | Embedded telemetry counters and loss detection coded in C/FreeRTOS and host software (Ege). Ozan verified zero-loss streaming on 18 Nov. | Execute extended stress tests under variable host CPU and USB bus loads. |
| | **C (Ege)** | Implement dataset playback path into phantom. | Software playback engine (`WavSource`, `StimulusRecord`), SHA-256 integrity checks, and resampled CirCor stimuli completed and regression-tested. | Drive physical playback through PAM8403 into acoustic phantom exciter. |
| **W08**<br>*(9–15 Nov)* | **A (Kaan)** | Measure frequency response of complete chain on phantom (swept sine). | Mathematical SISO $H_1$ FRF estimation and coherence workflows implemented in software (Ege). Physical bench test paused during midterm exam period. | Execute physical 20–500 Hz swept sine measurement on assembled phantom. |
| | **B (Ozan)** | Measure end-to-end latency and run 30-min continuous acquisition. | Firmware session limit audited (`G1_TARGET_SAMPLES = 480k` $\approx 10\text{ s}$, 40 s timeout). Software latency models implemented. Physical 30-min run paused. | Stage endurance firmware configuration to lift 10 s limit; run 30-minute stability test. |
| | **C (Ege)** | Implement automated test script for measurement and reporting. | Advisor metrology automation CLI (`pcg_core.metrology`), automated tables, and synthetic validation benchmarks completed and verified. | Run automated CLI on physical phantom sweep recordings. |
| **W09**<br>*(16–22 Nov)* | **A (Kaan)** | Feasibility test on phantom: recognizable S1/S2 heart sounds. | Completed physical breadboard wiring of INMP441 with ESP32-S3 (18 Nov). Demonstrated 23.2 dB in-band acoustic signal ratio in air. | Mount microphone inside chestpiece; validate S1/S2 transmission through phantom. |
| | **B (Ozan)** | Confirm continuous, correctly timestamped recording without clipping. | Verified 3.28 V supply rail with Agilent DMM. Flashed candidate firmware. Streamed 1,920,000 physical I²S samples across two sessions with 0 drops and 0 CRC errors. | Verify continuous acquisition during acoustic playback without amplifier distortion. |
| | **C (Ege)** | Compare captured waveform against source recording numerically. | Completed technical acceptance report for 18 Nov data. Hardened phantom runner CLI with anti-false-pass guards, strict ingest, and S1/S2 rhythm matching. | Execute end-to-end phantom test on physical bench with live audio playback. |

---

### 2. Summary of 18 November 2026 Physical Laboratory Integration

On Wednesday, 18 November 2026, the team conducted its first physical hardware session in the university laboratory following the two-week midterm exam recess:

1. **Hardware & Electrical Verification:**
   - Kaan wired the ESP32-S3-WROOM-1 and circular INMP441 MEMS microphone on a solderless breadboard.
   - Ozan verified the $3.3\text{ V}$ supply rail at **3.28 V** using a calibrated Agilent U1232A digital multimeter (within safe specification: 1.62 V – 3.63 V).
2. **Firmware Flashing & USB CDC Streaming:**
   - Firmware was flashed onto the ESP32-S3 over USB CDC on port `COM3`.
   - The team captured two 10.0-second physical sessions ($48\,000\text{ Hz}$, 32-bit slot, mono float32): a quiet ambient room baseline and an acoustic stimulus session.
   - Streaming continuity was confirmed: **0 in-stream dropped samples, 0 CRC failures, and 0 dropped frames across 1,920,000 samples** (40 seconds total acquisition).
3. **Acoustic Transduction in Air:**
   - The INMP441 microphone successfully transduced sound waves, yielding a **23.2 dB power ratio** in the 20–500 Hz cardiac passband between active sound and ambient silence.
   - High test volume resulted in minor near-clipping (0.2775% samples $> 0.98\text{ FS}$), demonstrating high transducer sensitivity.

---

### 3. Critical Academic Distinction: Microphone Bringup vs. Acoustic Phantom

> [!IMPORTANT]
> **Engineering Distinction:**
> - **What Succeeded (18 Nov):** Physical bringup of the digital microphone front-end (INMP441 $\to$ ESP32-S3 $\to$ USB CDC $\to$ PC) capturing acoustic sound through air.
> - **What Remains Pending:** The **Acoustic Phantom Experiment**. The vibration exciter, PAM8403 audio power amplifier, silicone/gelatin tissue-mimicking phantom block, and stethoscope chestpiece were not present on the bench.
> - **Feasibility Gate Status:** In accordance with course guidelines, the official Week 9 feasibility milestone requires recognizable S1/S2 heart sound transmission **through the acoustic phantom**. Therefore, the overall feasibility gate remains **CONDITIONALLY PENDING PHYSICAL PHANTOM BENCH TESTING**.

---

### 4. Next Steps for Next Laboratory Session

1. **Inventory Confirmation:** Physically confirm delivery and bench availability of the 30 mm exciter, PAM8403 amplifier, phantom coupling block, ultrasound gel, and stethoscope chestpiece.
2. **Bench Safety Audit:** Enforce independent 5V power for the PAM8403 (never from ESP32 rails) and verify BTL speaker output isolation (no ground connection).
3. **Execute Automated Feasibility Workflow:** Run `tools/hardware/run_phantom_pcg_experiment.py` to play CirCor reference recording `40058_AV.wav` through the phantom, capture via INMP441, and compute normalized cross-correlation ($\text{NCC} \ge 0.35$), coherence, and S1/S2 rhythm alignment.
