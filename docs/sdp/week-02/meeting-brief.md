# EEE495 â€” Week 02 Team Brief

- **Status:** DRAFT / WEEK-02
- **Last Updated:** 2026-09-29
- **Project Title:** Smart Digital Stethoscope: Heart Sound Acquisition, Signal Processing and Quality Assessment
- **Course:** EEE495 Senior Design Project I (followed by EEE496 Senior Design Project II)
- **Relevant GitHub Issue:** [#6 ([EEE495][W2] Prepare Week-3 component and interface decision meeting)](https://github.com/egecagintepe/ausculta-forge/issues/6)
- **Purpose:** Operational alignment document defining Week-02 responsibilities, individual deliverables, sourcing requirements, and inputs needed for the Week-03 decision meeting.

---

## 1. Current Week Context

- **Timeline:** Semester I â€” Week 2
- **Primary Objective:** Prepare sufficient technical evidence, architecture models, and verified Turkish component sourcing to make binding component and interface decisions in Week 3, ensuring all Group-A components are ordered before the Week-4 gate.

---

## 2. Module Ownership & Division of Responsibility

Assessment for EEE495/496 includes individual module quality, Git contribution history, and the ability to defend one's own module during oral defenses. Each module has one distinct owner:

| Module | Scope | Owner |
|---|---|---|
| **Module A** | Acquisition Hardware & Characterisation | **Kaan** |
| **Module B** | Embedded Acquisition & Data Path | **Ozan** |
| **Module C** | Computer Application & Quality Assessment | **Ege** |

---

## 3. This Week's Deliverables

### Kaan â€” Module A (Acquisition Hardware & Characterisation)
*Relevant Issue:* [#1 ([EEE495][W2][A] Heart-sound acquisition and transducer criteria)](https://github.com/egecagintepe/ausculta-forge/issues/1)

- **Deliverable A-W2-01: Heart-Sound Acquisition Technical Note**
  - Characterize relevant low-frequency PCG behavior (primary energy 20â€“200 Hz, murmurs/valve clicks up to 500 Hz).
  - Document major interference and noise sources (ambient acoustic room noise, friction/rubbing against chestpiece, muscle tremor, 50 Hz AC mains hum, sensor self-noise).
  - Detail acoustic/mechanical coupling considerations (bell vs diaphragm behavior, acoustic chamber resonance, compliant skin/tissue interface).
- **Deliverable A-W2-02: Microphone / Transducer Selection Criteria**
  - Electret Condenser Microphone (ECM) vs MEMS microphone comparison.
  - Mandatory low-frequency cutoff criterion: identify lower $-3\text{ dB}$ point (critical for capturing sub-50 Hz PCG signals).
  - Acoustic sensitivity, Acoustic Overload Point (AOP), and Signal-to-Noise Ratio (SNR) / Equivalent Input Noise (EIN).
  - Interface requirements (analog pre-amplifier needs vs digital I2S), supply voltage, and physical mounting within stethoscope chestpiece.
- **Deliverable A-W2-03: Acoustic Phantom Technical Requirements**
  - Small acoustic exciter / transducer specification capable of driving 20â€“500 Hz vibrations.
  - Small audio power amplifier drive requirements.
  - Compliant silicone or gel coupling layer specification (approximating chest wall acoustic impedance).
  - Rigid, repeatable mounting frame ensuring invariant chestpiece placement and contact pressure across runs.

> [!NOTE]
> Kaan does **NOT** own commercial pricing or Turkish vendor sourcing this week. Kaan establishes the technical criteria used by the team to evaluate Ozan's sourcing candidates.

---

### Ozan â€” Module B (Embedded Acquisition & Data Path)
*Relevant Issues:*
- [#2 ([EEE495][W2][B] Embedded acquisition architecture)](https://github.com/egecagintepe/ausculta-forge/issues/2)
- [#3 ([EEE495][W2][B] Turkey sourcing and BOM v0.1)](https://github.com/egecagintepe/ausculta-forge/issues/3)

- **Deliverable B-W2-01: Embedded Acquisition Data Path Architecture**
  - Define complete hardware-to-software chain:
    $$\text{Microphone/Input} \longrightarrow \text{ADC or I2S} \longrightarrow \text{MCU} \longrightarrow \text{DMA Ping-Pong Buffer} \longrightarrow \text{Continuity Counter/Timestamp} \longrightarrow \text{Native USB} \longrightarrow \text{Host PC}$$
  - Baseline nominal acquisition rate: 48 kHz continuous streaming.
- **Deliverable B-W2-02: Embedded Acquisition Research Note**
  - Investigate MCU audio sampling, circular/double DMA buffering, interrupt timing, and cache coherency.
  - Formulate sample continuity mechanism (monotonic packet sequence counter to detect buffer overflows and transport drops).
  - Evaluate ESP32-S3 Native USB transport options: USB CDC-ACM (virtual COM port) vs USB Vendor Bulk endpoint.
  - Define error reporting and status flags (DMA FIFO overflow, I2S sync loss, clipped samples).
- **Deliverable B-W2-03: Turkey Sourcing & BOM v0.1**
  - Ozan **explicitly owns** commercial sourcing, vendor identification, stock checking, and price tracking in Turkey.
  - Build BOM v0.1 table covering all **Group-A categories** with active local supplier links (e.g. Direnc.net, Robotistan, SAMM Market, Ozdisan).
  - For every item record: Category, Exact Product Name, Manufacturer, Exact Part Number, Turkish Supplier, URL, Quantity, Unit Price (TRY), Total Price (TRY), Stock Status, Estimated Delivery, Alternative Candidate, and Technical Justification.
  - **Group-A Categories to Source:**
    1. Acoustic stethoscope (donor chestpiece / tubing)
    2. Electret microphone candidates ($\times 2$)
    3. MEMS microphone candidates ($\times 2$, analog and/or I2S)
    4. Low-noise audio operational amplifiers ($\times 5$, e.g. OPA134, TLV9062, NE5532)
    5. Passive component kit (precision resistors, film/ceramic capacitors)
    6. MCU development boards ($\times 2$, ESP32-S3 exposing Native USB)
    7. Small acoustic exciter / vibration transducer (for phantom)
    8. Small audio power amplifier module (e.g. PAM8403 or LM386 board for phantom drive)
    9. Compliant silicone / gel coupling material
    10. Rigid phantom frame construction material
    11. Solderless breadboards and jumper wire assortments
    12. Shielded audio cables and connectors (3.5 mm / BNC / USB)
  - **STRICT DIRECTIVE:** DO NOT place orders during Week 02. BOM v0.1 is for team evaluation in Week 3.
- **Deliverable B-W2-04: Department Laboratory Equipment Audit**
  - Survey Bilkent EEE department laboratories to confirm availability of:
    - Digital storage oscilloscope (DSO)
    - Arbitrary function / waveform generator
    - Digital multimeter (DMM)
    - Temperature-controlled soldering station
    - USB audio interface / sound card
    - Reusable breadboards / lab dev-boards
  - Borrowed university laboratory equipment must be kept out of project purchase expenses.

---

### Ege â€” Module C (Computer Application & Quality Assessment)
*Relevant Issues:*
- [#4 ([EEE495][W2][C] Module-C status and B-to-C interface requirements)](https://github.com/egecagintepe/ausculta-forge/issues/4)
- [#5 ([EEE495][W2][C] Mandatory measurement and quality plan)](https://github.com/egecagintepe/ausculta-forge/issues/5)

- **Deliverable C-W2-01: Module-C Status Document**
  - Published at [`docs/sdp/week-02/module-c-status.md`](module-c-status.md).
  - Formal audit of existing repository assets; core work separated from advanced segmentation research; hardware dependencies cataloged.
- **Deliverable C-W2-02: Module B $\to$ Module C Interface Requirements**
  - Published at [`docs/sdp/week-02/bc-interface-requirements.md`](bc-interface-requirements.md).
  - Draft v0.1 defining host data ingest requirements (monotonic continuity, container bit depth, overflow flags) without prematurely freezing wire packet format.
- **Deliverable C-W2-03: Mandatory Measurement & Recording Quality Plan**
  - Published at [`docs/sdp/week-02/measurement-quality-plan.md`](measurement-quality-plan.md).
  - Formalized protocols for the six advisor-mandated physical measurements (frequency response, SNR, repeatability $\ge 10$ runs, mains interference, latency, dropped packets).
- **Deliverable C-W2-04: Project Management & Issue Coordination**
  - Established Week-02 GitHub project tracking, standardized label taxonomy, and issues [#1](https://github.com/egecagintepe/ausculta-forge/issues/1)â€“[#6](https://github.com/egecagintepe/ausculta-forge/issues/6).
- **Scope Restriction:**
  - **No new segmentation, AI, or GUI feature development** during Week 02 unless resolving a blocking defect in an existing core path.

---

## 4. Next Meeting Required Inputs & Agenda

### Required Inputs for Week-03 Meeting:
1. **Kaan brings:** Microphone/transducer technical criteria note + Acoustic phantom technical requirements.
2. **Ozan brings:** Embedded acquisition data path diagram + Turkey Sourcing Table & BOM v0.1 + Department equipment audit.
3. **Ege brings:** Module-C status report + B-to-C interface requirements draft + Mandatory measurement plan.

### Week-03 Meeting Action Items:
- Compare transducer candidates against Kaan's technical criteria and Ozan's local availability data; select primary and secondary microphone candidates.
- Confirm MCU dev board selection (ESP32-S3 with native USB).
- Confirm phantom physical design and acoustic exciter components.
- Review B-to-C interface requirements; collaboratively draft initial device-to-PC frame format.
- Upgrade BOM v0.1 to purchase-ready BOM v1.0 to prepare for the Week-4 ordering gate.

---

## 5. Upcoming Course Project Gates

```text
Week 02 (Current): Technical research, requirements draft, BOM v0.1 sourcing.
   â”‚
   â–¼
Week 03: Component selection, frame format draft, BOM v1.0 finalization.
   â”‚
   â–¼
Week 04 GATE: Requirements frozen, components selected, components ordered, tools available.
   â”‚
   â–¼
Week 05 GATE: Bench setup operational, known test signal captured end-to-end.
   â”‚
   â–¼
Week 09 FEASIBILITY GATE: Phantom PCG capture with recognisable S1/S2 acoustic structure.
   â”‚                       (If unrecognisable: fix transducer/coupling before adding features).
   â–¼
Week 13: Baseline device operational end-to-end (Phantom -> HW -> MCU -> PC App),
         initial characterization complete, interim report underway.
```
