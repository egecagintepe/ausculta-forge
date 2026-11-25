# W10 Module B: Gain and Filter Control Support

- **Week:** 10
- **Module:** B (Embedded Acquisition & Data Path)
- **Owner:** Özgür Ozan Yıldız
- **Status:** PLANNED / VERIFICATION PROTOCOL READY (Physical execution scheduled for 25 Nov 2026)

---

## 1. Objective

Verify analog gain adjustment (PAM8403 input sensitivity calibration) and digital filter preset support across the embedded-to-host acquisition link, ensuring the analog front-end operates linearly without digital clipping while maintaining adequate signal-to-noise separation ($>12\text{ dB}$).

---

## 2. Inputs & Dependencies

- **Firmware Release:** Tested G2 firmware release candidate (`firmware/releases/g2_candidate_20261117`).
- **Hardware Platform:** ESP32-S3 DevKit + INMP441 + PAM8403 amplifier ($12\ \Omega$ exciter).
- **Instruments:** Calibrated / verified multimeter for 3.3V LDO power rail verification.
- **Protocol:** AuscultaForge Profile B framing (1068 bytes/frame, 256 samples/frame, CRC-32).

---

## 3. Work Performed Prior to Lab Session

1. **Electrical Safety & LDO Rails:** Specified multimeter verification check for the INMP441 VDD supply ($3.14\text{ V} \le V_{\text{DD}} \le 3.46\text{ V}$). Prohibited connection to unverified DC supplies or AC mains.
2. **Gain Headroom & Clipping Thresholds:** Analyzed 18 November physical evidence (Run 3/4 near-clipping at $0.0575\%$, peak at $0.999967\text{ FS}$). Established strict laboratory protocol: PAM8403 potentiometer must start at minimum volume and be advanced only until the active-to-quiet ratio reaches $\ge 12\text{ dB}$, maintaining near-clipping below $0.05\%$.
3. **Filter Mode Interoperability:** Reviewed digital filter passband mappings for host processing:
   - Bell Mode: $20\text{--}120\text{ Hz}$ (mitral murmurs, low-frequency gallops).
   - Diaphragm Mode: $100\text{--}500\text{ Hz}$ (aortic regurgitation, lung sounds, high-frequency clicks).
   - Characterization / Flat Mode: $20\text{--}500\text{ Hz}$ (unfiltered baseline metrology).

---

## 4. Evidence & Documentation

- Lab Run Sheet: [`LAB_RUN_SHEET_2026-11-25.md`](../../../engineering/hardware/LAB_RUN_SHEET_2026-11-25.md)
- Firmware Release Manifest: `firmware/releases/g2_candidate_20261117/firmware_build_manifest.json`
- Technical Specification: `docs/sdp/week-09/submissions/module-b-ozan/W09_B_system-design-technical-specification_REV04_2026-11-20.docx` (canonical 38-page REV04-QA specification).

---

## 5. Results & Execution State

- **Physical Gain Verification:** `NOT_EXECUTED` (Scheduled for 25 November 2026 morning lab session).
- **Embedded Telemetry Status:** Verified in software and previous physical sessions (zero packet drops, clean CRC validation, exact 256-sample framing).

---

## 6. Open Decisions & Risks

- **Analog Potentiometer Non-Linearity:** The PAM8403 integrated potentiometer has logarithmic/non-linear taper; fine adjustments must be made manually in small increments.
- **USB Power Ripple:** USB supply noise from laptop chargers may introduce 50 Hz/100 Hz harmonics; laptop must run on battery power if mains noise exceeds $-20\text{ dBFS}$.

---

## 7. Next Week Handoff

Provide clean, unclipped physical recordings with documented multimeter voltages to Module C for quality threshold evaluation and repeatability testing in Week 11 (`W11_B_repeatability-and-spread.md`).
