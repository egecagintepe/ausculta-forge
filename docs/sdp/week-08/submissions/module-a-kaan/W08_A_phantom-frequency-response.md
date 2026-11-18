# W08 Module A: Phantom Frequency Response

- **Week:** 8 (9–15 November 2026)
- **Module:** A (Acquisition Hardware and Characterisation)
- **Owner:** Kaan
- **Official Module Role:** Transducer comparison, analogue front end, mechanical coupling, chestpiece, acoustic phantom construction, and bench measurements.
- **Status:** NOT EXECUTED (DEPENDENT ON W07 PHYSICAL PHANTOM BUILD)

---

## 1. Objective (Planned vs. Syllabus)

According to the official project plan (`SDP4_Digital_Stethoscope_Plan_EN.docx`):
> *"Week 8 Module A: Measure the frequency response of the complete chain on the phantom using a swept signal."*

The goal was to drive a calibrated sinusoidal sweep (20–500 Hz) through the acoustic exciter and phantom medium, record the transmitted acoustic pressure via the chestpiece and INMP441 microphone, and compute the magnitude and phase frequency response function (FRF) and coherence of the acoustic acquisition chain.

---

## 2. Inputs & Dependencies

- Fully assembled acoustic phantom (Module A Week 7 dependency — unbuilt).
- Audio power amplifier (PAM8403) and 30 mm surface exciter.
- Stethoscope chestpiece with acoustic coupling gel.
- Calibrated swept-sine stimulus (`software/pcg_core/stimulus.py:generate_log_sweep`).
- Signal processing FRF estimation script (`software/pcg_core/metrology/workflows.py:compute_phantom_frf`).

---

## 3. Work Performed During Week 8 (9–15 November 2026)

- **Calendar Context:** Week 8 coincided with the second week of the university midterm examination recess.
- **Substantiated Work & Limitations:**
  - Physical measurement of the phantom frequency response was **NOT EXECUTED** because the physical acoustic phantom (Week 7 dependency) had not been assembled.
  - No physical swept-sine signals were transduced through phantom tissue.
  - No synthetic data is fabricated or claimed as physical frequency response evidence.

---

## 4. Evidence & Contribution Breakdown

- **Software Metrology Preparation (Authored by Ege Çağın Tepe):**
  - Implemented SISO $H_1$ frequency response estimation, transfer function magnitude, phase, and Welch coherence calculation in `software/pcg_core/scientific/system_id.py` and `software/pcg_core/metrology/workflows.py`.
- **Module A Execution (Kaan):**
  - Bench measurement was blocked awaiting hardware procurement and physical phantom assembly.

---

## 5. Results & Compliance

- **Physical Frequency Response:** `NOT MEASURED`.
- **Metrology Software Pipeline:** Pass synthetic test harness (`software/tests/test_metrology_automation.py`), but awaiting physical phantom excitation data.

---

## 6. Subsequent Dated Follow-Up (18 November 2026 — Week 9)

On Wednesday, 18 November 2026, Kaan and Ozan performed the initial physical breadboard bringup of the INMP441 with ESP32-S3 in air:
- Evaluated acoustic sensitivity to room audio stimulus tones (`W09_A_feasibility-test.md`).
- Confirmed a 23.2 dB power ratio in the 20–500 Hz cardiac passband between active acoustic excitation and ambient quiet baseline.
- **Crucial Distinction:** This test confirmed that the digital MEMS microphone functions and transduces sound waves in air. It did **NOT** measure the frequency response of the acoustic phantom channel.

---

## 7. Open Decisions & Risks

1. **Exciter Linearity & Damping:** Electrodynamic exciters exhibit mechanical resonance peaks below 150 Hz when uncoupled; proper silicone/gelatin mass loading is required to obtain valid transfer function curves.
2. **Gain Setting:** PAM8403 input sensitivity must be calibrated to avoid driving the exciter into mechanical clipping.

---

## 8. Next Lab Handoff

Once the physical acoustic phantom is constructed, run `PHANTOM_LOG_SWEEP_20_500HZ_V1` through `tools/hardware/run_phantom_pcg_experiment.py` or the metrology CLI to produce the official Week 8 frequency response curve.
