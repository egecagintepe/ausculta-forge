# W07 Module A: Acoustic Phantom Build

- **Week:** 7 (2–8 November 2026)
- **Module:** A (Acquisition Hardware and Characterisation)
- **Owner:** Kaan
- **Official Module Role:** Transducer comparison, analogue front end, mechanical coupling, chestpiece, acoustic phantom construction, and bench measurements.
- **Status:** NOT EXECUTED DURING CALENDAR WEEK (PHYSICAL BUILD PENDING)

---

## 1. Objective (Planned vs. Syllabus)

According to the official project plan (`SDP4_Digital_Stethoscope_Plan_EN.docx`):
> *"Week 7 Module A: Build the acoustic phantom: a small transducer under a compliant coupling layer with the chestpiece above it."*

The goal was to assemble a physical acoustic test bench using an electrodynamic surface exciter bonded to an acoustic tissue-mimicking phantom (silicone or gelatin block), with a stethoscope chestpiece positioned on the upper surface to transfer acoustic vibrations to the microphone transducer.

---

## 2. Inputs & Dependencies

- Electrodynamic surface exciter (30 mm, 4–8 $\Omega$, 3–5 W) — Ordered / pending physical delivery.
- PAM8403 Class-D stereo audio power amplifier board.
- Compliant acoustic transmission medium (silicone elastomeric block or ballistic gelatin).
- Acoustic coupling gel (ultrasound transmission gel).
- Acoustic stethoscope chestpiece with diaphragm and bell.
- Mechanical mounting jig / clamps.

---

## 3. Work Performed During Week 7 (2–8 November 2026)

- **Calendar Context:** Week 7 coincided with the university midterm examination recess (2–15 November 2026).
- **Substantiated Work:**
  - Component specifications for the acoustic exciter and PAM8403 amplifier were reviewed against the project plan.
  - Physical assembly of the acoustic phantom was **NOT EXECUTED** during Week 7 due to pending receipt and physical bench verification of the exciter, coupling block, and chestpiece.
  - No physical measurements or acoustic tests were conducted during this calendar week.

---

## 4. Evidence & Contribution Breakdown

- **Physical Phantom Hardware:** None constructed during Week 7.
- **Contribution Attribution:**
  - Kaan: Module A lead; preliminary research on phantom materials and exciter specifications.
  - Physical assembly: `NOT EXECUTED`.
  - No synthetic data or unverified claims are reported as physical results.

---

## 5. Results & Compliance

- **Acoustic Phantom Status:** `PENDING PHYSICAL ASSEMBLY`.
- **Syllabus Milestone Alignment:** Week 7 physical phantom milestone was deferred due to component availability and the university midterm recess.

---

## 6. Subsequent Dated Follow-Up (18 November 2026 — Week 9)

On Wednesday, 18 November 2026, Kaan participated in the laboratory hardware session:
- Assembled the ESP32-S3 and INMP441 MEMS microphone on a breadboard and completed jumper wiring (`W09_A_feasibility-test.md`).
- Confirmed electrical and acoustic responsiveness of the standalone microphone to airborne audio test tones.
- **Crucial Distinction:** The 18 November laboratory session was a standalone microphone breadboard integration in air. It did **NOT** include the acoustic phantom (exciter, PAM8403, silicone block, or chestpiece).
- As of 18 November 2026, the physical acoustic phantom remains unbuilt and is prioritized for the next laboratory session.

---

## 7. Open Decisions & Risks

1. **Acoustic Coupling Material Selection:** A choice must be confirmed between casting silicone (e.g. Smooth-On Ecoflex 00-30) or a 10% food-grade ballistic gelatin block.
2. **Chestpiece Availability:** Physical possession of an acoustic stethoscope chestpiece must be verified before the next bench session.
3. **Electrical Safety:** The PAM8403 amplifier must be powered from an independent 5V supply and its BTL outputs must never be grounded.

---

## 8. Next Lab Handoff

Prioritize physical receipt and assembly of the exciter, amplifier, phantom block, and chestpiece according to [PHANTOM_BOM_AND_WIRING_CHECKLIST.md](../../../../engineering/hardware/PHANTOM_BOM_AND_WIRING_CHECKLIST.md) before attempting the Week 9 feasibility gate.
