# AuscultaForge — Acoustic Phantom BOM & Wiring Checklist

**Document ID:** `AF-BOM-PHANTOM-20261118`  
**Date:** 18 November 2026  
**Module Attribution:** Module A (Hardware/Kaan) & Module B (Embedded/Ozan)  
**Applicability:** AuscultaForge Physical Acoustic Phantom Bench Setup  
**Target Milestone:** SDP4 Week 9 Feasibility Gate

---

## 1. Acoustic Phantom Architecture & Signal Path

The acoustic phantom replaces human subject recording by providing a repeatable, ethical, and physically realistic acoustic transmission channel:

```
[ PC Host Workstation ]
        │ (Audio Line Out: Green 3.5 mm TRS Jack)
        ▼
[ Spliced AUX / 3.5 mm Breakout Cable ]
        │ (L_IN, GND; Unbalanced Line Level ~0.5–1.0 Vrms)
        ▼
[ PAM8403 Class-D Power Amplifier ] ◄─── [ Dedicated 5V Isolated Power Supply ]
        │ (Differential BTL Output: OUT_L+, OUT_L- — NEVER GROUNDED)
        ▼
[ 30 mm 12 Ω Vibration Exciter / Transducer ]
        │ (Mechanical acoustic vibrations via coupling gel)
        ▼
[ Compliant Acoustic Phantom Medium ] (Silicone / Ballistic Gelatin, ~30–40 mm thickness)
        │ (Acoustic pressure waves via coupling gel)
        ▼
[ Acoustic Stethoscope Chestpiece & Diaphragm ]
        │ (Airborne acoustic waves in sealed acoustic cavity)
        ▼
[ INMP441 Digital MEMS Microphone ] (Sealed acoustic port, 3.28 V VDD)
        │ (Digital I²S Audio: SCK=GPIO4, WS=GPIO5, SD=GPIO6)
        ▼
[ ESP32-S3 Microcontroller Board ] (Native USB-C CDC)
        │ (USB Packet Ingest: 24-bit PCM @ 48 kHz, 0 drop target)
        ▼
[ PC Host Acquisition & Analysis Application ]
```

---

## 2. Complete Bill of Materials (BOM)

### 2.1 Procured & On-Hand Components

| Ref ID | Description | Model / SKU | Source | Quantity | Status in Lab |
|---|---|---|---|---:|---|
| **MCU-01** | Microcontroller Board | ESP32-S3-WROOM-1-N16R8 (DSTK22852) | Direnc.net | 2 | Verified working in lab (`COM3` verified on 18 Nov; port must be dynamically discovered, never assumed static). |
| **MIC-01** | Digital I²S MEMS Microphone | SZYTF INMP441 circular breakout | Direnc.net | 3 | 1 breadboarded & verified (3.28 V measured); 2 spare units available. Keep acoustic port unobstructed. |
| **AMP-01** | Audio Power Amplifier Module | PAM8403 2×3 W Class-D mini module | Motorobit | 4 | **ORDERED / PHYSICAL INVENTORY NOT RECONFIRMED**. Documented in orders; physical bench check required. Enforce BTL isolation. |
| **EXC-01** | Surface Vibration Exciter | 30 mm 12 Ω resonance speaker | Motorobit | 2 | **ORDERED / PHYSICAL INVENTORY NOT RECONFIRMED**. Documented in orders; physical bench check required before soldering leads. |
| **CAB-01** | 3.5 mm TRS Analog Audio Cable | Juo braided AUX cable (1 m) | Amazon.com.tr | 1 | **ORDERED / PHYSICAL INVENTORY NOT RECONFIRMED**. Documented in orders; physical bench check required. |
| **PRT-01** | Solderless Breadboard | 830-point solderless breadboard | Direnc.net | 2 | In lab. Holds ESP32-S3 and INMP441 jumper routes. |
| **PRT-02** | Jumper Wires & Headers | M-M jumper set & 140-piece jumper kit | Direnc.net / Motorobit | Sets | In lab. Signal, ground, and rail routing. |
| **PRT-03** | Prototype Perfboard | 12×12 cm perforated board | Motorobit | 1 | In kit. Can serve as baseplate for amplifier. |

### 2.2 Missing Items Requiring Immediate Procurement

| Ref ID | Item Required | Recommended Specification | Indicative Source / Cost | Priority | Purpose & Functional Requirement |
|---|---|---|---|---|---|
| **CP-01** | Acoustic Stethoscope Chestpiece | Standard dual-head adult/pediatric stethoscope (metal bell + tunable diaphragm) | Pharmacy / Medical supply / Department stock (~150–250 TL) | **CRITICAL (P0)** | Acts as acoustic acoustic transformer/impedance matcher from phantom surface to air cavity. |
| **PH-01** | Acoustic Phantom Medium | Platinum-cure silicone (Ecoflex 00-30 / DragonSkin) OR 10% Knox Ballistic Gelatin mold (40 mm dia × 30 mm depth) | Medical silicone supplier OR grocery Knox gelatin mold (~40–120 TL) | **CRITICAL (P0)** | Provides human-tissue-mimicking acoustic velocity (~1540 m/s), density, and damping. |
| **GEL-01** | Acoustic Coupling Gel | Standard medical ultrasound transmission gel (250 ml bottle) | Local pharmacy / Medical supply (~50 TL) | **HIGH (P1)** | Eliminates micro air gaps at exciter–phantom and phantom–chestpiece contact surfaces. |
| **PWR-01** | Isolated 5 V Power Source | Standalone 5 V USB battery power bank OR bench DC linear power supply | Lab inventory / personal electronics (0 TL) | **HIGH (P1)** | Powers PAM8403 independently, isolating Class-D switching transients from ESP32 rail. |
| **JCK-01** | 3.5 mm Stereo Breakout Jack | 3.5 mm TRS female jack breakout board OR terminal block (or cut AUX cable) | Lab electronics kit / Direnc.net (~15–30 TL) | **MEDIUM (P2)** | Provides clean solder/screw connection from 3.5 mm cable to PAM8403 line input. |
| **FIX-01** | Mechanical Fixture / Weight | Standard laboratory retort stand with clamp OR calibrated 200 g contact weight | Physics/EE lab stock (0 TL) | **MEDIUM (P2)** | Ensures consistent 1.5–2.0 N coupling pressure during repeated trials. |

---

## 3. Step-by-Step Pin-by-Pin Wiring Checklist

### 3.1 PAM8403 Audio Amplifier Wiring

| PAM8403 Pin | Signal Description | Connects To | Wire Type / Color | Verified (Y/N) |
|---|---|---|---|---|
| `+5V` (VDD) | Amplifier Power (+5.0 V) | Isolated 5 V Power Supply (+) | Red wire (22–24 AWG) | [ ] |
| `GND` (Power) | Power Ground | Isolated 5 V Power Supply (-) | Black wire (22–24 AWG) | [ ] |
| `L_IN` | Left Channel Audio Input | 3.5 mm TRS Jack Tip (Left Audio) | Shielded / White wire | [ ] |
| `GND` (Audio) | Audio Input Ground | 3.5 mm TRS Jack Sleeve (Audio Ground) | Shield / Ground braid | [ ] |
| `R_IN` | Right Channel Audio Input | *Unused — leave open or tie to Audio GND* | None | [ ] |
| `OUT_L+` | Left Speaker Bridge Output (+) | 30 mm 12 Ω Exciter Terminal 1 | Red / Stripe wire | [ ] |
| `OUT_L-` | Left Speaker Bridge Output (-) | 30 mm 12 Ω Exciter Terminal 2 | Black / Solid wire | [ ] |
| `OUT_R+` | Right Speaker Bridge Output (+) | *UNCONNECTED — LEAVE FLOATING* | None | [ ] |
| `OUT_R-` | Right Speaker Bridge Output (-) | *UNCONNECTED — LEAVE FLOATING* | None | [ ] |

> [!CAUTION]
> **CRITICAL ELECTRICAL VERIFICATION CHECK BEFORE POWERING:**  
> With the circuit unpowered and DMM in resistance mode (Ω):
> 1. Measure resistance between `OUT_L-` and Circuit `GND`: Must read **OPEN / > 100 kΩ**.
> 2. Measure resistance between `OUT_L+` and Circuit `GND`: Must read **OPEN / > 100 kΩ**.
> 3. Measure resistance between `OUT_L-` and `OUT_R-`: Must read **OPEN / > 100 kΩ**.  
> If any terminal measures near 0 Ω to GND, **STOP IMMEDIATELY**. Do not apply power until the short is cleared.

### 3.2 INMP441 MEMS Microphone Wiring (Verified 18 Nov Baseline)

| INMP441 Pin | Pin Function | ESP32-S3 Pin / Rail | Breadboard Jumper Color | Measured Value / Requirement |
|---|---|---|---|---|
| `VDD` | Power Supply | ESP32-S3 `3V3` Pin | Orange | **3.15 V to 3.45 V** (3.28 V measured on 18 Nov) |
| `GND` | Digital Ground | ESP32-S3 `GND` Rail | Brown / Black | 0.00 V common reference |
| `L/R` | Channel Select | Common `GND` Rail | Brown jumper to GND | Tied low selects **Left slot** data stream |
| `SCK` | Continuous Serial Bit Clock | ESP32-S3 `GPIO4` | Yellow jumper | Clean square wave clock (1.536 MHz) |
| `WS` | Word Select (LRCLK) | ESP32-S3 `GPIO5` | Green jumper | 48.000 kHz frame sync |
| `SD` | Serial Audio Data Output | ESP32-S3 `GPIO6` | Purple jumper | 24-bit MSB-first serial data |

### 3.3 Mechanical & Acoustic Coupling Assembly

```
         [ 200 g Calibration Weight / Clamp ]
                         │
                         ▼
        ┌──────────────────────────────────┐
        │ Stethoscope Chestpiece (CP-01)   │
        │ ┌──────────────────────────────┐ │
        │ │ Sealed Cavity / Tubing Stub  │ │
        │ │     ▲                        │ │
        │ │     │ Acoustic seal          │ │
        │ │  [INMP441 Acoustic Port]     │ │
        │ └──────────────────────────────┘ │
        │ Diaphragm (Coupling face)        │
        └──────────────────────────────────┘
                         │
      ══════════════ [ Thin Gel Layer ] ══════════════
                         │
        ┌──────────────────────────────────┐
        │ Acoustic Phantom Medium (PH-01)  │
        │ (Silicone or Gelatin, 30 mm thk) │
        └──────────────────────────────────┘
                         │
      ══════════════ [ Thin Gel Layer ] ══════════════
                         │
        ┌──────────────────────────────────┐
        │ 30 mm 12 Ω Exciter (EXC-01)      │
        │ Rigid Backing / Baseplate        │
        └──────────────────────────────────┘
```

Acoustic Coupling Rules:
1. Apply a thin, bubble-free layer of ultrasound gel (`GEL-01`) between the exciter diaphragm face and the bottom phantom surface.
2. Apply a second thin gel layer between the top phantom surface and the stethoscope chestpiece diaphragm.
3. Ensure the INMP441 circular PCB is centered over the chestpiece stem cavity. Seal the perimeter with a soft silicone gasket, O-ring, or non-hardening acoustic putty.
4. **DO NOT** block the central sound entry hole of the INMP441.

---

## 4. Pre-Power Safety Checklist (Operator Sign-Off)

Before turning on the 5 V amplifier supply or connecting USB CDC:

- [ ] **BTL Floating Isolation Verified:** `OUT_L+` and `OUT_L-` have no continuity to circuit GND, chassis, or PC ground (> 100 kΩ).
- [ ] **Power Supply Isolation Verified:** PAM8403 is powered from a dedicated 5 V source, completely independent from ESP32-S3 3.3 V and 5 V rails.
- [ ] **Audio Ground Reference:** PC line-out ground connects strictly to PAM8403 Audio `GND`, not to speaker outputs.
- [ ] **Microphone VDD Verified:** ESP32-S3 `3V3` rail measured with DMM before connecting INMP441 (3.28 V ± 0.1 V).
- [ ] **Acoustic Port Clearance:** INMP441 underside acoustic hole is visually inspected and completely free of obstructions.
- [ ] **PC Audio Volume Preset:** PC output master volume is set to **20% (low volume initial setting)** to prevent accidental over-driving, clipping, or voice coil thermal stress.
- [ ] **Mechanical Stability:** Phantom and chestpiece are mechanically clamped with stable contact pressure without wobbling.
