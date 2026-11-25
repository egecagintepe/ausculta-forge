# AuscultaForge — Next Lab Physical Inventory Confirmation & Experiment Backlog

**Document ID:** `AF-HW-INV-20261118`  
**Date:** 18 November 2026  
**Auditors:** Ege Çağın Tepe (Module C), Kaan (Module A), Ozan (Module B)  
**Target Milestone:** Week 9 Physical Acoustic Phantom Feasibility Experiment

---

## 1. Inventory Confirmation Matrix

> [!CAUTION]
> **Inventory Verification Rule:**  
> Components marked `ORDERED` must **NOT** be treated as physically available until held in hand, inspected, and confirmed in this checklist. Do not assume the university lab possesses specialized consumables or acoustic components.

| Component / Item | Specification / Requirement | Procurement Status | In-Hand Physical Status (YES / NO / UNKNOWN) | Storage / Location | Responsible Member |
|---|---|---|---|---|---|
| **ESP32-S3 DevKit** | ESP32-S3-WROOM-1 N16R8, dual USB-C | In-Hand | **YES** (Verified 18 Nov) | Lab / Ege & Ozan | Ege / Ozan |
| **INMP441 MEMS Breakout** | Bottom-port omnidirectional I²S microphone | In-Hand | **YES** (Verified 18 Nov) | Lab breadboard | Kaan |
| **Solderless Breadboard & Jumpers** | Standard breadboard + M-M jumpers | In-Hand | **YES** (Verified 18 Nov) | Lab bench | Kaan |
| **USB-C Data Cable** | High-speed data cable (tested on COM3) | In-Hand | **YES** (Verified 18 Nov) | Lab bench | Ozan |
| **30 mm Vibration Exciter** | 12 $\Omega$, 3–5 W electrodynamic surface transducer | Ordered (f0f6b57) | **UNKNOWN / TO CONFIRM** | Shipped / with Kaan? | Kaan |
| **PAM8403 Audio Amplifier** | 2 × 3 W Class-D stereo breakout board | Ordered (f0f6b57) | **UNKNOWN / TO CONFIRM** | Shipped / with Kaan? | Kaan |
| **3.5 mm AUX Cable** | 3.5 mm male stereo plug to bare wire / split | Ordered | **UNKNOWN / TO CONFIRM** | Shipped / with Kaan? | Kaan |
| **Independent 5 V Power Supply** | 5V USB battery power bank or regulated DC supply | Lab Stock / Sourced | **UNKNOWN / TO CONFIRM** | Lab stock / bench | Ozan |
| **Stethoscope Chestpiece** | Galena Çift Taraflı Yetişkin (A-01, 283.00 TL) | Ordered (User-Reported) | **UNKNOWN / TO CONFIRM** | Shipped / with Kaan? | Kaan |
| **Acoustic Phantom Medium** | AnkaHobiMarket RTV-2 Kalıp Silikonu 500g (A-09, 350.00 TL) | Ordered (User-Reported) | **UNKNOWN / TO CONFIRM** | Shipped / with Kaan? | Kaan |
| **Acoustic Coupling Gel** | Ultrasound transmission gel (Aquasonic / generic) | Not Sourced | **NO** | Missing (RTV-2 is not gel) | Kaan |
| **Digital Multimeter** | Calibrated DMM (e.g. Agilent U1232A) | Lab Stock | **YES** (Available in Lab) | Electronics Lab | Ozan |
| **Multimeter Camera / Smartphone** | Camera to record rail voltage photos | Field Item | **YES** (Available) | Mobile | Ozan |
| **Mechanical Clamps / Weights** | 200–500 g mass for chestpiece coupling pressure | Lab Stock | **UNKNOWN / TO CONFIRM** | Mechanics Lab | Kaan |

---

## 2. Practical Specifications & Provisional Bench Alternatives (Exploratory / Uncalibrated)

> [!NOTE]
> **Metrological Status of Alternatives:**  
> The provisional substitutes listed below are uncalibrated bench exploratory alternatives intended solely for preliminary functional bringup. They must **NOT** be treated as formally measured acoustic equivalents of validated medical soft-tissue phantom standards without dedicated characterization.

### 2.1 Acoustic Phantom Medium
- **Primary Specification (REV04 Ordered):** **AnkaHobiMarket RTV-2 Kalıp Silikonu + Katalizör (500 g, 5 Shore, yarı şeffaf)** — 350.00 TL (Trendyol).
  - *Procurement Status:* User reported ordered (screenshot on file); official invoice and delivery confirmation pending. Supersedes historical 3 mm silicone sheet candidate (1,173.00 TL) to prevent double counting.
  - *Chemical / Mechanical Caveat:* RTV-2 is a two-part liquid condensation-cure silicone requiring exact catalyst proportion per the manufacturer's instruction sheet / product label upon unboxing (do not assume a fixed generic ~2–4% ratio), degassing, and $\ge 12\text{–}24\text{ hours}$ curing time. It is **NOT ultrasound gel** and **NOT a ready-made solid sheet**. Mechanical behavior and acoustic impedance must be evaluated on a cured sample puck.
- **Provisional Bench Alternative (Exploratory):** **10% Ballistic Gelatin Block**.
  - Preparation: 100 g food-grade gelatin (Bloom 250) dissolved in 900 mL heated distilled water ($60^\circ\text{C}$), optionally with 50 mL glycerin to prevent dehydration, cast in a flat rectangular container and chilled for $\ge 4\text{ hours}$.
  - Acoustic Impedance: Estimated $\approx 1.5\text{–}1.6\times 10^6\text{ Pa}\cdot\text{s/m}$ (literature approximation for preliminary acoustic coupling, uncalibrated).

### 2.2 Acoustic Coupling Gel
- **Primary Specification:** Medical ultrasound transmission gel (e.g. Parker Aquasonic 100, carbomer-based).
- **Provisional Bench Alternative (Exploratory):** High-viscosity generic aloe vera gel ($>98\%$ purity) or pure glycerin.
  - Requirement: Eliminates micro-air gaps between chestpiece diaphragm and phantom medium during preliminary bringup without introducing air bubbles; acoustic attenuation is uncalibrated. Note that RTV-2 liquid silicone CANNOT be used as coupling gel.

### 2.3 Stethoscope Chestpiece
- **Primary Specification (REV04 Ordered):** **Galena Çift Taraflı Profesyonel Yetişkin Steteskop** (A-01) — 283.00 TL (Trendyol MEDICATION).
  - *Procurement Status:* User reported ordered (screenshot on file); official invoice and physical delivery confirmation pending. Supersedes historical Medikaltec candidate (679.99 TL) to prevent double counting.
  - *Application:* Flexible tubing will be detached from the chestpiece stem to couple the INMP441 MEMS microphone acoustic port into the internal acoustic chamber.
- **Provisional Bench Alternative (Exploratory):** Any working mechanical acoustic stethoscope (e.g. 3M Littmann Classic II/III or generic Sprague Rappaport) borrowed for bench testing.

### 2.4 Independent 5 V Amplifier Power Supply
- **Primary Specification:** Regulated laboratory linear or low-ripple switched DC bench power supply set to $5.00\text{ V}$, current limit $1.0\text{ A}$.
- **Recommended Bench Alternative:** Dedicated $5\text{ V}$ USB battery power bank equipped with a commercial USB-A to screw-terminal breakout board or barrel-jack adapter.
- **WIRING SAFETY HAZARD:** Avoid loose, stripped wire ends or makeshift cut cables to prevent accidental power short-circuits or reverse-polarity damage to the PAM8403.
- **CRITICAL RESTRICTION:** Under **NO CIRCUMSTANCES** may the PAM8403 be powered from the ESP32-S3 $3\text{V}3$ or $5\text{V}$ pins. The amplifier draws transient currents up to $800\text{ mA}$, which will induce voltage dips, reset the MCU, and corrupt audio sampling.

### 2.5 Procurement Total Reconciliation (REV04 as of 2026-11-20)
- **Historical REV03 Working Baseline:** **3,613.21 TL** (contains an unconfirmed 90.00 TL estimate for Motorobit perfboards).
- **New Items Added (REV04):** Galena Stethoscope (283.00 TL) + RTV-2 Silicone (350.00 TL) = **633.00 TL**.
- **Current Provisional Total:** **4,246.21 TL** (or **4,156.21 TL** if the 90.00 TL unconfirmed estimate is excluded).
- **Audit Rule:** Neither total represents fully audited expense until tax invoices and actual charged amounts (shipping/coupons) are reconciled. Historical candidates are not accumulated.

---

## 3. Pre-Lab Electrical & Mechanical Safety Checklist

Before connecting audio cables or switching on power at the next session:

```
[ ] 1. PAM8403 BTL Ground Isolation Check:
       With multimeter in continuity mode:
       - Confirm resistance between OUT+ and GND is OPEN (OL / > 1 MOhm).
       - Confirm resistance between OUT- and GND is OPEN (OL / > 1 MOhm).
       - Confirm resistance between OUT- and OUT+ is OPEN (OL).
       DANGER: Grounding OUT- will immediately destroy the PAM8403 output stage!

[ ] 2. Common Ground Connection:
       - Connect PAM8403 input signal GND to the PC line-out sleeve GND.
       - Connect 5V power supply return to PAM8403 GND.
       - ESP32-S3 GND remains isolated on USB ground.

[ ] 3. Exciter Mechanical Coupling:
       - Bond the 30 mm exciter's flat surface firmly to the bottom face of the phantom block.
       - Use double-sided thin adhesive film or mechanical clamp; avoid soft foam tape that absorbs vibration.

[ ] 4. Microphone Sound Port Sealing:
       - The INMP441 bottom sound port must face into the acoustic chamber of the chestpiece.
       - Secure with acoustic sealing putty (Blu-Tack) around the rim to prevent room noise leakage into the chamber.

[ ] 5. Digital Multimeter Voltage Log & Photo:
       - Measure ESP32-S3 3.3V rail and take a clear photograph of the DMM display showing 3.28V to satisfy documentation criteria.
```

---

## 4. Prioritized Remaining Experiments Backlog

In accordance with course milestones and technical dependencies, the remaining physical experiments must be conducted in the following strict order:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. Material Procurement & Electrical Isolation Safety Verification      │
│    Prerequisites: Kaan/Ozan physical inventory in hand.                 │
│    Blocker: Unconfirmed possession of exciter, PAM8403, and chestpiece. │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│ 2. Physical Acoustic Phantom Assembly                                   │
│    Prerequisites: Verified materials from Step 1.                       │
│    Blocker: Bubble-free gelatin/silicone casting; mechanical mounting.  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│ 3. PCG Playback & Physical INMP441 Acquisition                          │
│    Prerequisites: Assembled phantom + PC audio line-out to PAM8403.     │
│    Tool: tools/hardware/run_phantom_pcg_experiment.py                   │
│          --port <DISCOVERED_CDC_PORT> --quiet-session <path>            │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│ 4. S1/S2 Morphological Validation (The Official Week 9 Gate)            │
│    Prerequisites: Completed Step 3 physical capture.                    │
│    Criteria: NCC >= 0.35, Coherence >= 0.40, Match >= 70%, Jitter <= 45ms│
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│ 5. Physical Frequency Response, In-Band SNR & Gain Characterization     │
│    Prerequisites: Passed Step 4 feasibility gate.                       │
│    Tool: python -m pcg_core.metrology.cli (Swept-sine 20-500 Hz).       │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│ 6. Latency, Repeatability & 30-Minute Continuous Endurance Testing      │
│    Prerequisites: Lift firmware 10s/40s session limit in Week 10 sprint.│
│    Blocker: G1_TARGET_SAMPLES = 480000U architectural cap in g1.h.      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Detailed Breakdown of Experiment Stages:

1. **Experiment 1: Material Procurement & Safety Verification**
   - **Prerequisites:** Physical delivery and bench inspection of ordered parts.
   - **Blockers:** Missing chestpiece, phantom block, coupling gel, or unconfirmed exciter/PAM8403 delivery.
   - **Success Criteria:** All rows in Table 1 marked `YES`, DMM verifies BTL isolation (> 1 M$\Omega$).
2. **Experiment 2: Physical Acoustic Phantom Assembly**
   - **Prerequisites:** All Table 1 items confirmed; DMM isolation verified.
   - **Blockers:** Poor mechanical bonding or air gap between exciter and phantom medium.
   - **Success Criteria:** Rigid mechanical assembly holding exciter, phantom block, and chestpiece under ~200 g constant pressure.
3. **Experiment 3: Known PCG Playback & Physical INMP441 Acquisition (Two-Step Workflow)**
   - **Prerequisites:** Assembled phantom connected to PC audio line out; ESP32-S3 connected on native USB CDC. Port dynamically identified via `python -m serial.tools.list_ports`.
   - **Step A — Quiet Baseline Recording:** Capture a 10.0 s ambient resting baseline first to establish the quiescent floor:
     ```powershell
     # Capture 10s quiet session and record its resulting path (e.g. experiments/hardware/session_quiet.json)
     ```
   - **Step B — Synchronized Stimulus Playback & Capture:**
     ```powershell
     python tools/hardware/run_phantom_pcg_experiment.py `
         --port <DISCOVERED_CDC_PORT> `
         --reference data/raw/week6_real_pcg_20261026/circor/40058_AV.wav `
         --quiet-session <path_to_quiet_session> `
         --play-audio `
         --verify-audio-routing `
         --operator "Kaan_Ozan_Ege"
     ```
   - **Mandatory SNR Rule:** Without `--quiet-session`, in-band acoustic SNR cannot be calculated and the runner marks the SNR gate as `INCONCLUSIVE_NO_QUIET_BASELINE`, strictly preventing false physical gate passes.
   - **Blockers:** Audio routing failure; USB CDC communication drops.
   - **Success Criteria:** Complete 10.0 s capture (480,000 samples @ 48 kHz) with strictly 0 in-stream dropped samples and 0 CRC failures.
4. **Experiment 4: S1/S2 Morphological Validation (Week 9 Feasibility Gate)**
   - **Prerequisites:** Clean physical capture from Experiment 3 with certified `--quiet-session`.
   - **Blockers:** High ambient room noise, acoustic clipping ($> 0.05\%$), or decoupled chestpiece.
   - **Success Criteria:** In-band SNR $\ge 12\text{ dB}$, envelope contrast $\ge 2.0$, peak count ratio $0.5$–$1.8$, peak match fraction $\ge 70\%$, mean jitter $\le 45\text{ ms}$, $\text{NCC} \ge 0.35$, yielding official status `PHYSICAL_GATE_PASSED`.
5. **Experiment 5: Physical Frequency Response & Noise Characterization**
   - **Prerequisites:** Passed Experiment 4 feasibility gate.
   - **Blockers:** Nonlinear amplifier saturation; lack of swept-sine reference calibration.
   - **Success Criteria:** SISO $H_1$ transfer function magnitude, phase, and coherence computed over 20–500 Hz; active-to-quiescent SNR $\ge 12.0\text{ dB}$.
6. **Experiment 6: Extended Endurance, Latency & Repeatability Characterization**
   - **Prerequisites:** Firmware sprint to lift the $10\text{ s}$ / $40\text{ s}$ watchdog cap (`firmware/components/g1/g1.c`).
   - **Blockers:** Firmware session architecture; thermal or buffer overrun over 30 minutes.
   - **Success Criteria:** 30 continuous minutes ($86\,400\,000\text{ samples}$) streamed with strictly 0 dropped packets; 10 repeated phantom runs with $\text{CV} \le 15\%$.

---

## 5. Immediate Member Actions Before Next Bench Session

1. **Kaan (Module A Lead):**
   - Confirm receipt and physical location of the 30 mm vibration exciter and PAM8403.
   - Source or borrow an acoustic stethoscope chestpiece.
   - Prepare the phantom medium (either casting silicone or 10% gelatin block) and obtain acoustic coupling gel.
2. **Ozan (Module B Lead):**
   - Provide an independent 5V power source (USB power bank or lab bench supply).
   - Prepare smartphone/camera for multimeter rail photo documentation.
3. **Ege (Module C Lead):**
   - Provide laptop with pre-tested `run_phantom_pcg_experiment.py` and CirCor reference stimulus `stimulus_pcg_48000hz.wav`.
