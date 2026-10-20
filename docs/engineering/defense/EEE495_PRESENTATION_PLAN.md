# AuscultaForge — EEE495 Capstone Presentation Plan (Semester I)
**Document ID:** `AF-PRES-EEE495-PLAN-V01`  
**Classification:** `ACADEMIC_PRESENTATION`  
**Course:** EEE495 Senior Design Project I  
**Department:** Electrical and Electronics Engineering  
**Primary Presenter / Document Owner:** Ege Çağın Tepe (Module C Owner)  
**Baseline Git Commit:** `fa4b75a80d29aab04875534234574db9f6c0af43`

---

## 1. Executive Summary & Presentation Strategy

The EEE495 presentation marks the conclusion of Semester I (Foundation, Architecture, Transducer Selection, Procurement, and Host Platform Bring-Up). The primary grading criteria for Semester I are:
1. Clear, non-clinical engineering problem formulation.
2. Objective transducer candidate evaluation (ECM vs Digital MEMS).
3. Verifiable embedded architecture and host software ingestion.
4. Transparent procurement closeout and laboratory bench readiness.
5. Absolute honesty regarding physical vs. simulated progress.

---

## 2. The 3-Minute Elevator Pitch (Executive Overview)

> *"Good morning, members of the examination committee. I am Ege Çağın Tepe, representing the AuscultaForge senior design team alongside Kaan in Module A and Ozan in Module B.*
> 
> *AuscultaForge is an engineering research platform developed to investigate the complete acquisition and metrology chain of a digital stethoscope for cardiac phonocardiography ($20\text{--}500\text{ Hz}$).*
> 
> *Rather than jumping straight to unverified machine learning on dirty signals, our project focuses on physical acoustic fidelity. In Module A, Kaan evaluated electret condenser microphones versus digital I2S MEMS, establishing that integrated 24-bit MEMS sensors bypass breadboard analog electromagnetic noise. In Module B, Ozan architected an ESP32-S3 acquisition datapath using hardware I2S Direct Memory Access and native USB CDC-ACM streaming at 48,000 samples per second. In Module C, I developed the host software platform: a FastAPI desktop bridge, a bounded peak-preserving display pipeline running at 60 FPS, lossless dual-file session recording with SHA-256 sidecars, and an automated metrology suite executing the six mandatory physical measurements.*
> 
> *Our integrated software test suite passes 394 automated tests, and with our Week 04 component procurement from DirencNet complete, we are fully positioned for Academic Week 05 acoustic phantom bench bring-up. Thank you."*

---

## 3. The 10-Minute Technical Slide-by-Slide Outline

| Slide # | Slide Title | Key Visual / Diagram | Presenter & Talking Points |
|---|---|---|---|
| **1** | Title & Team Identity | Project logo, academic affiliations | **All:** Formal introduction; EEE495 Digital Stethoscope. |
| **2** | Project Scope & Non-Clinical Boundary | In-Scope vs. Out-of-Scope matrix | **Ege:** Phonocardiography ($20\text{--}500\text{ Hz}$) only; phantom metrology, non-clinical. |
| **3** | End-to-End System Architecture | Full system block diagram (Mermaid) | **Ege:** Acoustic front-end $\to$ I2S $\to$ ESP32-S3 DMA $\to$ USB CDC-ACM $\to$ Python DSP. |
| **4** | Transducer Selection (Module A) | ECM vs. INMP441 comparison table | **Kaan:** Sallen-Key pre-amp noise on breadboard vs. digital 24-bit MEMS on silicon. |
| **5** | Procurement & Turkish Sourcing BOM | BOM v0.2, DirencNet orders (PR #28) | **Ozan:** Substitution of PUI Audio with INMP441 due to local stock; DevKit N16R8. |
| **6** | Embedded Acquisition & DMA (Module B) | FreeRTOS dual-core task map | **Ozan:** Core 1 I2S DMA ping-pong buffering ($10.67\text{ ms}$); Core 0 USB CDC-ACM. |
| **7** | Host Runtime & Display Decimation | Display pipeline diagram | **Ege:** Peak-preserving decimation ($\le 600$ pts) protecting 60 FPS React canvas. |
| **8** | Lossless Recording & Integrity | WAV + JSON sidecar schema | **Ege:** Whole-file SHA-256 storage hashing; verification and replay integrity. |
| **9** | Metrology & The 6 Mandatory Tests | Measurement matrix table | **Ege:** Automated 6-measurement runner; current status: `HARDWARE_UNVERIFIED`. |
| **10**| Verification & Week 05 Bring-Up Plan | Pytest summary (394 passed), G1 gate | **All:** 394 tests passed; physical bring-up checklist ready for lab bench. |

---

## 4. The 25-Minute In-Depth Academic Defense Breakdown

* **Minutes 00–05: Problem Formulation & Acoustic Physics (Kaan & Ege)**
  * Anatomy of $S_1, S_2$; frequency spectrum ($20\text{--}500\text{ Hz}$).
  * Why lung sounds ($> 500\text{ Hz}$) are excluded.
  * Acoustic phantom tissue-mimicking silicone requirements.
* **Minutes 05–10: Front-End Electronics & Transducer Evaluation (Kaan)**
  * Transducer evaluation matrix: Electret JFET pre-amplifier vs. INMP441 I2S MEMS.
  * Microphonic chestpiece coupling and mechanical air-seal design.
* **Minutes 10–15: Embedded Hardware & Data Transport (Ozan)**
  * ESP32-S3 dual-core Xtensa LX7 architecture; I2S DMA linked-list descriptors.
  * USB CDC-ACM full-speed endpoints; sequence counter continuity tracking.
  * Procurement closeout and DirencNet board verification.
* **Minutes 15–20: Host Software, DSP & Metrology Architecture (Ege)**
  * FastAPI application factory (57 routes) and WebSocket streaming bridge.
  * 4th-order SOS Butterworth causal streaming bandpass filter.
  * Peak-preserving display decimation and UI backpressure isolation.
  * Dual-file persistence (24-bit WAV + SHA-256 JSON sidecar).
  * SISO system identification $H_1(f)$, delay estimation, and coherence.
* **Minutes 20–25: Verification Atlas & Committee Q&A (All)**
  * Evidence review: 394 automated tests, C golden vectors, virtual bench.
  * Reiteration of physical hardware status (Week 05 bring-up gate).
