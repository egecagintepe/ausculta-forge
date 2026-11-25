# W10 Module A: Transducer Characterisation and Comparison

- **Week:** 10
- **Module:** A (Acquisition Hardware & Acoustic Characterisation)
- **Owner:** Ünal Kaan Öztürk
- **Status:** PLANNED / EXPERIMENTAL DESIGN PREPARED (Physical lab execution scheduled for 25 Nov 2026)

---

## 1. Objective

Compare the frequency response, acoustic sensitivity, and signal-to-noise ratio of the primary digital MEMS transducer (INMP441, bottom-port omnidirectional, I2S 24-bit) against an analog comparator transducer / standard acoustic stethoscope chestpiece on the RTV-2 silicone acoustic phantom across the cardiac frequency band ($20\text{--}500\text{ Hz}$).

---

## 2. Inputs & Dependencies

- **Acoustic Phantom:** 12 cm diameter $\times$ 10 mm nominal thickness RTV-2 silicone specimen (`docs/engineering/hardware/specimen_rtv2_20261123.json`).
- **Acoustic Actuator:** 30 mm $12\ \Omega$ exciter driven by PAM8403 audio amplifier.
- **Transducers:**
  - Primary: INMP441 digital I2S MEMS microphone mounted on breakout board with acoustic seal ring.
  - Comparator (if available): Analog electret capsule / traditional stethoscope acoustic head.
- **Fixtures:** 100 g and 200 g calibrated test loads for repeatable contact pressure.
- **Measurement Protocol:** `docs/engineering/hardware/W10_LAB_MEASUREMENT_PLAN_2026-11-25.md`.

---

## 3. Work Performed Prior to Lab Session

1. **Mechanical Mounting & Loading Protocol:** Designed a standardized contact fixture utilizing a 12 cm Borcam flat mold. Defined two-tier static loading ($100\text{ g} \approx 0.65\text{ kPa}$, $200\text{ g} \approx 1.29\text{ kPa}$ nominal pressure for $44\text{ mm}$ head area) to assess contact acoustic coupling without deforming the phantom.
2. **Acoustic Roll-off Audit:** Inspected the INMP441 manufacturer datasheet; identified the typical $-3\text{ dB}$ low-frequency roll-off corner at approximately $60\text{ Hz}$. Noted that below $60\text{ Hz}$ ($20\text{--}50\text{ Hz}$), acoustic sensitivity drops, requiring clear notation rather than synthetic software equalization.
3. **Fallback Barrier Protocol:** Prepared a dry compliant medical silicone pad fallback procedure in case the 23 November RTV-2 specimen remains tacky on the morning of 25 November.

---

## 4. Evidence & Documentation

- Measurement Plan: [`W10_LAB_MEASUREMENT_PLAN_2026-11-25.md`](../../../engineering/hardware/W10_LAB_MEASUREMENT_PLAN_2026-11-25.md)
- Operator Run Sheet: [`LAB_RUN_SHEET_2026-11-25.md`](../../../engineering/hardware/LAB_RUN_SHEET_2026-11-25.md)
- Phantom Fabrication Log: [`PHANTOM_FABRICATION_LOG_2026-11-23.md`](../../../engineering/hardware/PHANTOM_FABRICATION_LOG_2026-11-23.md)
- Historical baseline: 18 November 2026 physical INMP441 acoustic recordings (Runs 1–4).

---

## 5. Results & Execution State

- **Physical Comparative Measurement:** `NOT_EXECUTED` (Scheduled for 25 November 2026 morning lab session).
- **Baseline Transducer Characterisation:** INMP441 MEMS baseline physically proven on 18 Nov ($23.2\text{ dB}$ active/quiet ratio on Run 1, $8.0\text{ dB}$ on Run 4). Secondary transducer comparison pending physical hardware session.

---

## 6. Open Decisions & Risks

- **Secondary Transducer Availability:** If only the INMP441 transducer is operational in tomorrow's laboratory, the baseline MEMS characterisation and phantom frequency response will be executed, and comparator curves will be marked `NOT_AVAILABLE` without fabricating data.
- **Airborne Acoustic Leakage:** Ensure ambient room speech is silenced during sweeps to prevent room reflections from dominating the phantom transmission path.

---

## 7. Next Week Handoff

Upon acquisition of comparative transducer datasets in Week 10, hand off multi-transducer recordings to Module C for automated quality threshold calibration (`W10_C_quality-threshold-calibration.md`).
