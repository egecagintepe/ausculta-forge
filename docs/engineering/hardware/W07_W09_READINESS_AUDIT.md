# AuscultaForge — Weeks 7–9 Physical Feasibility Readiness Audit

**Document ID:** `AF-AUDIT-W0709-20261118`  
**Date:** 18 November 2026  
**Module Attribution:** Cross-Module Engineering Audit (Module A: Kaan, Module B: Ozan, Module C: Ege)  
**Project Baseline:** `ausculta-forge` repository HEAD `4a658fa`  
**Academic Course:** EEE 495 — Senior Design Project I  
**Target Milestone:** SDP4 Week 9 Feasibility Gate (Acoustic Phantom PCG Playback & Acquisition)

---

## 1. Executive Summary & Gate Status

The AuscultaForge project has finalized the academic progress report for Weeks 1–6 and completed the physical verification of the primary digital transducer chain on 18 November 2026. The 18 November lab session confirmed that the ESP32-S3 (N16R8) and the INMP441 MEMS microphone communicate deterministically over I²S and stream loss-free 24-bit audio at 48 kHz over native USB CDC (`COM3` on the lab laptop; port numbers are dynamically assigned by Windows and must always be discovered dynamically rather than assumed static across machines), producing a 23.2 dB spectral power difference under acoustic stimulation.

However, in accordance with the official project specification (`SDP4_Digital_Stethoscope_Plan_EN.docx`) and the departmental evaluation rules (`SDP_Assessment_Criteria_for_Students.docx`):

> **SDP Assessment Criteria — Week 9 Gate:**  
> *"The core model or acquisition chain is validated against a case whose answer is known independently. Nothing built after this point can be trusted without it. Validation by inspection is not accepted."*

> **SDP4 Digital Stethoscope Plan — Milestone (Week 9):**  
> *"Feasibility gate. A phonocardiogram played through the phantom must be captured with recognisable first and second heart sound structure. If this is not achieved, the transducer type or position is changed before any further work, and the scope is reduced if necessary."*

**Gate Declaration:**  
The 18 November physical G2 test (ambient loudspeaker tone in free air) satisfied the **transducer functional sanity check**, but it does **NOT** satisfy the **Week 9 Feasibility Gate**. The Week 9 milestone requires playing an independently known clinical phonocardiogram (CirCor / PhysioNet dataset) through a physical acoustic phantom and capturing it with recognizable S1 and S2 heart sound morphology.

This audit evaluates the physical inventory, identifies missing items, establishes safety requirements for the exciter and PAM8403 amplifier, documents the firmware session duration limitation, and provides an actionable blueprint for the upcoming physical experiment.

---

## 2. Component Inventory & Physical Readiness

Based on the verified order register (`docs/sdp/week-04/W04_B_actual-orders_2026-10-16_v01.csv`), the procurement closeout (`docs/sdp/week-04/procurement-closeout.md`), and the physical lab returns of 18 November 2026:

| Component | Part / Model | Quantity | Procurement / Stock Status | Physical Readiness in Lab | Action Required |
|---|---|---|---|---|---|
| **Microcontroller Board** | ESP32-S3-WROOM-1-N16R8 (DSTK22852) | 2 units | Purchased (Direnc.net) | **VERIFIED WORKING** (Board #1 running candidate G2 firmware, USB CDC `COM3` verified on 18 Nov; port must be dynamically discovered) | Ready for phantom experiment. Spare board available. |
| **Digital MEMS Microphone** | SZYTF INMP441 circular breakout | 3 units | Purchased (Direnc.net) | **VERIFIED WORKING** (Unit #1 wired on breadboard, 3.28 V measured, I²S active) | Unit #1 ready; 2 spare units unmounted. Keep acoustic port unobstructed. |
| **Vibration Exciter** | 30 mm 12 Ω vibration/resonance speaker | 2 units | Ordered (Motorobit) | **ORDERED / PHYSICAL INVENTORY NOT RECONFIRMED** | Documented in order ledger; physical presence at lab bench requires operator confirmation before assembly. |
| **Audio Power Amplifier** | PAM8403 2×3 W Class-D mini module | 4 units | Ordered (Motorobit) | **ORDERED / PHYSICAL INVENTORY NOT RECONFIRMED** | Documented in order ledger; physical presence at lab bench requires operator confirmation before assembly. Solder headers and enforce BTL isolation. |
| **Analog Audio Cable** | Juo 3.5 mm TRS AUX cable (1 m) | 1 unit | Ordered (Amazon.com.tr) | **ORDERED / PHYSICAL INVENTORY NOT RECONFIRMED** | Documented in order ledger; physical presence at lab bench requires operator confirmation before assembly. |
| **Acoustic Stethoscope Chestpiece** | Dual-head acoustic stethoscope (bell + diaphragm) | 0 units | **NOT ORDERED / MISSING** | **ABSENT** | Procure donor stethoscope chestpiece (medical supply/pharmacy or department stock) or use temporary machined/3D-printed acoustic cup. |
| **Acoustic Phantom Medium** | Silicone block (Ecoflex 00-30 / DragonSkin) or Ballistic Gelatin | 0 units | **NOT ORDERED / MISSING** | **ABSENT** | Prepare tissue-mimicking phantom (standard 10% Knox/bovine ballistic gelatin block or platinum-cure silicone pad). |
| **Acoustic Coupling Gel** | Medical ultrasound / acoustic transmission gel | 0 units | **NOT ORDERED / MISSING** | **ABSENT** | Procure standard ultrasound transmission gel (Aquasonic or generic 250 ml bottle, ~50 TL) to eliminate air gaps. |
| **Phantom Mechanical Clamp/Frame** | Rigid fixture to maintain stable coupling pressure | 0 units | **NOT ORDERED / MISSING** | **ABSENT** | Construct rigid laboratory clamp or weighted collar (~1.5–2.0 N / ~200 g) to hold chestpiece firmly against phantom. |
| **Dedicated 5 V Power Supply** | Clean 5 V USB power bank or regulated bench PSU | Department | Lab stock | **LAB STOCK / TO BE RECONFIRMED** | Ensure dedicated isolated 5 V supply for PAM8403 is confirmed present before bench setup. |
| **Lab Measurement Tools** | DMM, Oscilloscope, Function Generator | Department | Available in lab | **AVAILABLE** | DMM verified (3.28 V recorded on 18 Nov). Oscilloscope ready for PAM8403 drive verification. |

### Critical Missing Items Summary:
1. **Stethoscope Chestpiece (Donor Assembly):** Essential for acoustic impedance matching between the compliant phantom surface and the MEMS sensor cavity.
2. **Tissue-Mimicking Phantom Medium:** A compliant solid medium (gelatin or silicone, ~50 mm diameter × 30 mm thickness) providing human-tissue-like acoustic propagation speed (~1540 m/s) and attenuation.
3. **Acoustic Coupling Gel:** Necessary to eliminate micro-air gaps between exciter face and phantom, and between phantom and chestpiece diaphragm.
4. **3.5 mm Line-In Breakout:** Solderable 3.5 mm stereo audio jack or terminal block to connect PC audio out to PAM8403 input pins cleanly without loose wire fraying.

---

## 3. Safe Wiring & Electrical Integrity Requirements

### 3.1 PAM8403 Bridge-Tied Load (BTL) Warning — MANDATORY

> [!CAUTION]
> **NEVER GROUND THE SPEAKER OUTPUTS OF THE PAM8403!**  
> The PAM8403 is a filterless Class-D stereo audio power amplifier utilizing **Bridge-Tied Load (BTL)** outputs (`OUT_L+`, `OUT_L-`, `OUT_R+`, `OUT_R-`).  
> In a BTL configuration, neither speaker terminal is at ground potential; both terminals switch between 0 V and +5 V in anti-phase at ~250 kHz PWM.  
> **Connecting `OUT_L-` or `OUT_R-` to circuit GND, to PC ground, to an oscilloscope ground clip, or to each other will immediately short the low-side internal MOSFETs and destroy the amplifier chip!**

Wiring Rules for PAM8403:
- Connect the 12 Ω vibration exciter exclusively across `OUT_L+` and `OUT_L-` (differential connection).
- Leave the unused channel (`OUT_R+` / `OUT_R-`) completely open and unconnected.
- If probing the speaker output with an oscilloscope, use a **differential probe**, or probe `OUT_L+` and `OUT_L-` on two separate channels with math subtraction (`CH1 - CH2`), with probe ground clips connected strictly to PAM8403 DC `GND`, never to speaker terminals.

### 3.2 Power Supply & Ground Separation

> [!WARNING]
> **DO NOT POWER THE PAM8403 FROM THE ESP32-S3 DEVELOPMENT BOARD!**  
> Under dynamic excitation, the PAM8403 driving a 12 Ω load draws peak transient currents up to 600–800 mA.  
> Powering the amplifier from the ESP32-S3 `3V3` pin will destroy the on-board linear regulator (AP2112/AMS1117).  
> Powering the amplifier from the ESP32-S3 `5V` (VBUS) pin will introduce massive switching spikes into the USB rail, triggering USB brownout resets and corrupting I²S digital sampling.

Power Architecture:
1. **ESP32-S3 + INMP441 Rail:** Powered exclusively via the native USB CDC cable connected to the PC workstation. The ESP32-S3 internal regulator supplies 3.28 V to the INMP441 `VDD`.
2. **PAM8403 Amplifier Rail:** Powered exclusively from an independent, floating 5 V source (e.g., a standalone USB battery power bank or an isolated bench DC power supply set to 5.0 V with a 1.0 A current limit).
3. **Ground Reference:** The only shared ground between the PC audio output and the PAM8403 is the analog audio ground (`L_IN_GND`) at the amplifier input.

### 3.3 INMP441 Acoustic Port Preservation

> [!IMPORTANT]
> The INMP441 is a **bottom-port** MEMS microphone. The acoustic entry aperture is located on the underside of the metallic MEMS package, aligned with the central through-hole in the circular breakout PCB.  
> - Do not place tape, adhesive putty, or solder flux across the central hole.  
> - When mounting into the acoustic chamber, the seal must form a perimeter ring around the hole, leaving the central cavity completely open to airborne sound pressure waves.

---

## 4. Firmware Architecture Constraints & 30-Minute Endurance Analysis

The official project syllabus sets two distinct temporal requirements:
1. **Week 9 Feasibility Gate:** Capture a known PCG through the phantom with recognizable S1/S2 heart sound structure.
2. **Week 8 Embedded Requirement:** *"Measure the end to end latency and run a continuous acquisition of at least thirty minutes."*

### 4.1 Current Firmware Configuration
Inspection of the current candidate firmware (`firmware/components/g1/include/g1.h` and `firmware/components/g1/g1.c`):
- `G1_TARGET_SAMPLES` is defined as `480000U` (line 6 of `g1.h`). At 48,000 Hz, this represents exactly **10.0 seconds** of continuous acquisition.
- `g1.c:192` enforces a hard watchdog timer:
  ```c
  if ((s->state == G1_STREAMING || s->state == G1_STOPPING) &&
      now - s->reference_us > 40000000U) {
      s->telemetry.stop_reason = STOP_REASON_TIMEOUT;
      g1_transport_fault(s);
      return;
  }
  ```
  This 40,000,000 µs (40.0 s) hard timeout terminates any streaming session that exceeds 40 seconds.

### 4.2 Impact Assessment & Academic Honesty
- **For Week 9 PCG Feasibility Gate:** The 10.0-second / 480,000-sample limit is **fully sufficient**. Standard clinical heart sound recordings (such as CirCor DigiScope `40058_AV.wav`, duration 11.89 s) fit comfortably within a 10.0 s acquisition window, capturing 8 to 12 complete cardiac cycles.
- **For Week 8 30-Minute Continuous Run Requirement:** The current firmware **cannot** run for 30 minutes without hitting either `G1_TARGET_SAMPLES` completion or the 40-second watchdog fault.  
  - *Engineering Resolution:* In the Week 10 firmware sprint (Module B / Ozan), the firmware protocol will be extended with an explicit continuous mode (`target_samples = 0xFFFFFFFFFFFFFFFF` or multi-session auto-chaining) and an adjustable watchdog timer.
  - *Academic Integrity Note:* We do not fabricate or claim a 30-minute endurance pass for Week 8. The 30-minute endurance run remains documented as **PENDING FIRMWARE PROTOCOL EXTENSION**.

---

## 5. Milestone Alignment Matrix (Weeks 7–9)

| Week / Milestone | Official Plan Requirement | Current Actual Engineering State | Gate / Acceptance Status |
|---|---|---|---|
| **Week 7 (Module A - Kaan)** | Build the acoustic phantom: small transducer under compliant coupling layer with chestpiece above it. | Exciter and PAM8403 in lab inventory; chestpiece and silicone medium unprocured. Mechanical coupling unbuilt. | **BACKLOGGED / IN PROGRESS** (Preparing runbook and BOM). |
| **Week 7 (Module B - Ozan)** | Implement device status reporting and packet loss detection. | Firmware telemetries (`in_stream_dropped_samples`, CRC, sequence continuity) fully implemented and verified on 18 Nov (0 drops over 1.92M samples). | **COMPLETED & VERIFIED**. |
| **Week 7 (Module C - Ege)** | Implement playback path so dataset recording can be driven into phantom. | Software stimulus generators, polyphase resampling, and PC playback path implemented in `pcg_core.stimulus`. | **COMPLETED & VERIFIED**. |
| **Week 8 (Module A - Kaan)** | Measure frequency response of complete chain on phantom using swept signal. | Software log sweep generator (20–500 Hz) ready in `pcg_core.phantom`; physical measurement pending phantom assembly. | **PENDING PHYSICAL PHANTOM**. |
| **Week 8 (Module B - Ozan)** | Measure end-to-end latency and run continuous acquisition of at least 30 minutes. | Latency decomposition logic ready; 30-minute continuous run blocked by firmware 10 s / 40 s watchdog limit. | **BLOCKED BY FIRMWARE LIMIT / DEFERRED TO W10**. |
| **Week 8 (Module C - Ege)** | Implement automated test script that records, measures, and writes results table. | `software/pcg_core/validate_capture.py` and `tools/hardware/run_phantom_pcg_experiment.py` implemented. | **COMPLETED & VERIFIED**. |
| **Week 9 (Module A - Kaan)** | Run feasibility test. If it fails, change transducer position or type. | Primary breadboard I²S wiring verified; phantom acoustic feasibility test pending physical setup. | **PENDING PHYSICAL LAB SESSION**. |
| **Week 9 (Module B - Ozan)** | Confirm recording is continuous, correctly timestamped, and free of clipping. | Ingest pipeline verifies 0 sequence gaps, near-clipping fraction (<0.05%), and steady-state RMS. | **READY FOR EXPERIMENT**. |
| **Week 9 (Module C - Ege)** | Compare captured waveform against source recording and report similarity numerically. | Cross-correlation alignment, Welch coherence, band energy ratios, and Shannon envelope S1/S2 analysis ready. | **READY FOR EXPERIMENT**. |
| **MILESTONE (Week 9 Gate)** | **Core acquisition chain validated against an independently known PCG with recognizable S1/S2 structure.** | 18 Nov G2 test verified electrical link and room sound pickup. Physical PCG phantom test ready for execution. | **OPEN / GATE PENDING EXECUTION**. |

---

## 6. Recommendations & Action Items

1. **Procure Chestpiece & Acoustic Medium (Immediate — Kaan):**
   - Acquire a standard acoustic stethoscope chestpiece (dual-head adult or pediatric).
   - Prepare a 10% Knox/bovine ballistic gelatin block or cast a 40 mm diameter Ecoflex silicone puck.
   - Procure standard ultrasound transmission gel.
2. **Solder PAM8403 & Exciter Interface (Immediate — Ozan):**
   - Solder pin headers on one PAM8403 board.
   - Solder 20 cm flexible twisted-pair leads to the 30 mm 12 Ω vibration exciter.
   - Solder a 3.5 mm TRS audio cable to PAM8403 `L_IN` and `GND`.
   - Verify zero DC connection between speaker terminals and GND with DMM.
3. **Execute Automated Phantom Experiment (Ege, Kaan, Ozan):**
   - Follow `docs/engineering/hardware/W09_PHYSICAL_PCG_FEASIBILITY_RUNBOOK.md`.
   - Use `tools/hardware/run_phantom_pcg_experiment.py` to drive CirCor `40058_AV.wav` into the phantom and capture audio simultaneously over USB CDC.
   - Document quantitative cross-correlation, coherence, and S1/S2 peak identification.
