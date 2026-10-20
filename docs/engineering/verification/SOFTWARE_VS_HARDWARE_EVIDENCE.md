# AuscultaForge — Software Evidence vs. Physical Hardware Reality
**Document ID:** `AF-VERIF-SW-VS-HW-V01`  
**Classification:** `CODE_VERIFIED` / `HARDWARE_UNVERIFIED`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Baseline Git Commit:** `fa4b75a80d29aab04875534234574db9f6c0af43`

---

## 1. Academic Integrity & Evidence Classification Policy

In undergraduate capstone defenses, examination panels frequently challenge students to separate what has been demonstrated in software simulation from what has been physically measured on real silicon and bench hardware.

AuscultaForge enforces an uncompromising scientific evidence boundary:
* **Zero Fabricated Numbers:** No numerical PASS values, SNR ratios, or frequency response curves are reported as physical facts until measured on the physical bench.
* **Evidence Classification Tags:**
  * `CODE_VERIFIED`: Confirmed directly by inspecting integrated, committed source code.
  * `TEST_VERIFIED`: Validated through observed, passing automated software tests on this workstation.
  * `HARDWARE_UNVERIFIED`: Requires physical MCU silicon, acoustic sensors, and phantom hardware.
  * `DOCUMENTED_PROPOSAL`: Specified in design documents, but not yet approved or implemented.

---

## 2. Software Verification Status (Proven by Automated Tests on Workstation)

The following capabilities are **`CODE_VERIFIED` and `TEST_VERIFIED`** by automated test suites:
* **Host Processing Throughput:** Confirmed capable of processing $48,000 \text{ samples/s}$ continuously with $< 5\%$ CPU utilization.
* **Causal Filtering Stability:** Confirmed that 4th-order SOS Butterworth bandpass filtering preserves phase continuity without edge spikes across contiguous 512-sample blocks.
* **Peak-Preserving Display Decimation:** Verified that transient clicks are retained while decimating to $\le 600$ points for 60 FPS browser rendering.
* **Session Integrity & Cryptography:** Verified that every recorded WAV file is hashed with SHA-256 and verified upon replay.
* **State Machine Invariants:** Verified that the host runtime prevents illegal streaming transitions and recovers gracefully from simulated disconnects.
* **Metrology Automation Pipeline:** Verified that automated test scripts successfully compute Welch PSD, SISO transfer functions, delays, and CSV/Markdown reports from input audio streams.
* **Portable C Parity:** Verified that C11 bit-manipulation routines produce bit-for-bit identical results to Python normalization.

---

## 3. Physical Hardware Realities (Pending Physical Bench Delivery)

The following items are **`HARDWARE_UNVERIFIED`** and require laboratory verification during Academic Week 05:
1. **Physical DirencNet ESP32-S3 Board Routing:**
   * It is unknown whether the delivered DirencNet board is an authentic dual-USB DevKitC-1 with native OTG PHY routed out, or a single-port clone requiring a custom breakout cable to `GPIO 19/20`.
2. **Real INMP441 Acoustic Noise Floor:**
   * The manufacturer specifies $61 \text{ dBA}$ SNR, but the actual physical noise floor when mounted inside the 3D-printed acoustic chestpiece on a silicone phantom has **not yet been measured**.
3. **I2S Clock Jitter on Jumper Wires:**
   * Solderless breadboards introduce capacitive loading and signal reflections on high-speed lines (`SCK` at $3.072 \text{ MHz}$). Physical oscilloscope probing is required.
4. **USB CDC-ACM Windows Latency Under Bus Contention:**
   * Sustained physical streaming latency over Windows USB host controllers must be measured using a digital storage oscilloscope.

---

## 4. The Six Mandatory Advisor Physical Measurements (Current Status)

The course advisor mandates **six primary physical measurements** to characterize the digital stethoscope prototype. These measurements CANNOT be satisfied by software simulations:

| # | Mandatory Measurement | Target Passband / Metric | Physical Prerequisites | Current Status | Expected Value / Course Target |
|---|---|---|---|---|---|
| **1** | **Phantom Frequency Response** | SISO Magnitude $|H_1(f)|$ & Coherence $\gamma_{xy}^2(f)$ ($20\text{--}500\text{ Hz}$) | Audio exciter + Silicone phantom + PAM8403 amp + INMP441 mounted in chestpiece | **NOT YET MEASURED** | Flat within $\pm 6 \text{ dB}$ across $50\text{--}250 \text{ Hz}$; $\gamma_{xy}^2 > 0.8$. |
| **2** | **Signal-to-Noise Ratio (SNR)** | Active PCG stimulus vs. quiescent noise floor in relative dB | Transducer coupled to silent phantom; exciter driven at calibrated nominal level | **NOT YET MEASURED** | $\ge 30 \text{ dB}$ bandlimited SNR ($20\text{--}500\text{ Hz}$). |
| **3** | **Measurement Repeatability** | Statistical dispersion ($s, \text{CV}$) across $\ge 10$ independent runs | Calibrated 500 g dead-weight clamp fixture on phantom; automated test runner | **NOT YET MEASURED** | Coefficient of Variation $\text{CV} \le 5.0\%$ across all 10 runs. |
| **4** | **Mains Interference Level** | High-resolution spectral quantification of 50 Hz & harmonics in dBFS | Digital stethoscope on phantom; varied USB shielding and ground bonding | **NOT YET MEASURED** | Mains fundamental $\le +15 \text{ dB}$ above local baseline acoustic floor. |
| **5** | **End-to-End Latency** | Propagation delay from electrical excitation to host buffer ingestion | Dual-channel oscilloscope probing exciter terminal vs. host GPIO output | **NOT YET MEASURED** | Total end-to-end latency $\le 50 \text{ ms}$ (software baseline $\approx 21\text{ ms}$). |
| **6** | **Dropped-Packet Rate** | 100% sample continuity during prolonged continuous acquisition | Continuous 30-minute streaming test (Week 8 gate) over physical Native USB | **NOT YET MEASURED** | **Zero dropped blocks** ($0.0\%$ packet loss) over 30 minutes ($86,400,000$ samples). |

> [!IMPORTANT]
> **EXAMINATION DEFENSE INVARIANT:**
> If an examiner asks: *"What was your measured physical SNR?"*
> **Correct Defense Answer:**
> *"The physical SNR has not yet been measured on real hardware because our DirencNet components were just procured in Week 04 and physical bench bring-up is scheduled for Week 05. However, our software metrology pipeline (`pcg_core.metrology`) is verified with automated tests and ready to calculate the metric automatically as soon as the first phantom WAV session is recorded."*
