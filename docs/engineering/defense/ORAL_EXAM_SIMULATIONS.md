# AuscultaForge — Oral Examination Defense Simulations
**Document ID:** `AF-DEFENSE-SIMULATIONS-V01`  
**Classification:** `ACADEMIC_DEFENSE`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Target Candidate:** Ege Çağın Tepe (Module C Owner)

---

## 1. Overview of the Oral Examination Format

The EEE495/EEE496 capstone defense typically lasts 30–45 minutes. A panel of three faculty examiners rotates through deep technical interrogation. This document provides three realistic, word-for-word simulated defense transcripts modeling the specific personalities, technical focuses, and trap questions commonly encountered.

---

## Simulation 1: The Tough Digital Signal Processing Professor

**Examiner Profile:** Specialist in stochastic signal processing, spectral estimation, and filter design. Skeptical of machine learning claims without solid classical DSP foundations.

* **Professor:** *"Ege, I see you are sampling heart sounds at 48 kHz. Heart sounds rarely exceed 500 Hz. Why are you wasting memory and bandwidth sampling at 48 kHz when Nyquist says 1,000 Hz is sufficient?"*
* **Candidate (Ege):** *"Professor, from a strict Nyquist perspective, 1,000 Hz would avoid aliasing for a 500 Hz signal. However, from a hardware implementation perspective, 48 kHz is the standard master audio clock rate generated cleanly by the ESP32-S3 audio PLL without fractional dividers. Furthermore, the INMP441 MEMS microphone internal decimation filter requires a minimum bit clock frequency ($f_{\text{SCK}} \ge 1.024\text{ MHz}$), which at 32 bits per channel slot mandates higher sample rates. Finally, 48x oversampling spreads the ADC quantization noise power across a 24 kHz Nyquist band, improving our in-band Signal-to-Quantization-Noise Ratio by approximately 16.8 dB before our digital bandpass filter even runs."*
* **Professor:** *"Fair enough on the oversampling. Now, looking at your bandpass filter in `pcg_core/dsp.py`, you implemented a 4th-order Butterworth IIR filter. Why didn't you use `scipy.signal.filtfilt` to achieve zero phase distortion?"*
* **Candidate (Ege):** *"Because `filtfilt` is non-causal: it requires filtering the signal forward and then backward in time, which requires having the entire future signal in memory. In our live workstation, we are streaming audio in real-time at 60 FPS. A real-time filter must be causal. We used `scipy.signal.sosfilt` with persistent filter state vectors ($z_k$) across 512-sample blocks. This preserves phase continuity across block boundaries without edge spikes, incurring a causal group delay of only about 3.2 ms. We only use zero-phase filtering offline when analyzing pre-recorded sessions."*
* **Professor:** *"Good. Now step to the whiteboard. Show me the Welch PSD estimator equation and explain why you used a Hann window instead of a rectangular window."*
* **Candidate (Ege):** *(Writes equation on whiteboard)*
  $$\hat{S}_{xx}(f) = \frac{1}{K} \sum_{i=0}^{K-1} \frac{1}{U M} \left| \sum_{n=0}^{M-1} x_i[n] w[n] e^{-j 2\pi f n / f_s} \right|^2$$
  *"A rectangular window has a Dirichlet kernel spectrum whose sidelobes roll off at only $-6 \text{ dB/octave}$, with the first sidelobe at $-13.3 \text{ dB}$. In a heart sound, low-frequency $S_1$ and $S_2$ peaks at 50 Hz can be 30 dB stronger than a systolic murmur at 200 Hz. The rectangular sidelobes would leak across the spectrum and completely submerge the murmur. The Hann window's sidelobes roll off at $-18 \text{ dB/octave}$ (first sidelobe at $-31.5 \text{ dB}$), keeping the high-frequency floor clean."*
* **Professor:** *"Very well. Next examiner."*

---

## Simulation 2: The Embedded Systems & Computer Architecture Professor

**Examiner Profile:** Specialist in microcontrollers, real-time operating systems (RTOS), and computer buses. Focuses on race conditions, memory corruption, and hardware timing.

* **Professor:** *"Ege, let's look at `tools/esp32_bench_example/README.md`. Earlier in your sprint documentation, there was a mention of generating 48 kHz samples using `512 samples + vTaskDelay(11 ms)`. Why did your final acceptance patch explicitly flag that as UNVERIFIED and non-viable for production?"*
* **Candidate (Ege):** *"Because FreeRTOS task delays are quantized by the operating system tick rate. On the ESP32-S3, standard `CONFIG_FREERTOS_HZ` is 100 Hz, meaning one tick is 10 ms. A delay of 11 ms rounds up to 20 ms (2 ticks) or suffers from severe scheduler jitter depending on when the tick interrupt fires. A software delay loop can never guarantee a strict, continuous 48.000 kHz sampling rate. In production firmware, sampling must be driven entirely by hardware I2S DMA interrupts where physical crystal clock transitions pace data into SRAM without CPU intervention."*
* **Professor:** *"Correct. Now, you receive 24-bit audio inside a 32-bit container. If bit 23 is 1, how do you handle it in C? What happens if you do `(int32_t)(raw << 8) >> 8`?"*
* **Candidate (Ege):** *"Left-shifting a negative signed value is undefined behavior under ISO C99 §6.5.7/4. Furthermore, right-shifting a negative signed integer is implementation-defined; while GCC typically performs an arithmetic shift, the standard does not guarantee it. In our portable C implementation (`golden_common.h`), we operate strictly on `uint32_t`. We check if bit 23 is set (`raw & 0x00800000U`), and if true, we bitwise OR with `0xFF000000U` to set bits 31..24 to 1s, then cast the result to `int32_t`. This is guaranteed to be safe and portable across all C compilers."*
* **Professor:** *"What is the difference between internal SRAM and PSRAM on the ESP32-S3 N16R8, and why can't DMA buffers go into PSRAM?"*
* **Candidate (Ege):** *"Internal SRAM is on-chip memory directly accessible by the DMA controller over internal buses with single-cycle latency. PSRAM is external pseudo-static RAM connected over an Octal SPI bus. The ESP32-S3 I2S DMA controller cannot write directly to external PSRAM because DMA requires internal DMA-capable SRAM. Our ping-pong buffers are strictly allocated in internal SRAM."*
* **Professor:** *"Excellent. I have no further questions."*

---

## Simulation 3: The Capstone Committee Chair & Academic Auditor

**Examiner Profile:** Focuses on project management, procurement integrity, academic boundaries, and individual contribution tracking.

* **Professor:** *"Ege, this repository looks very extensive, but let's be blunt: has your team actually captured heart sounds from a living human patient with this device?"*
* **Candidate (Ege):** *"No, Professor. And I want to emphasize that human clinical trials were explicitly excluded from our project scope by design. AuscultaForge is an undergraduate engineering prototype designed to evaluate acoustic characterization, transducer selection, and transmission metrology on bench acoustic phantoms. Testing on human subjects requires Institutional Review Board (IRB) ethics approval, medical device electrical isolation certification, and clinical protocols that are outside our approved scope. All physical testing is conducted on acoustic silicone phantoms."*
* **Professor:** *"Then what is this 'CirCor Pediatric PCG Validation' in your codebase?"*
* **Candidate (Ege):** *"That is an algorithm benchmark running on the open-access PhysioNet CirCor pediatric database to validate our Springer LR-HSMM segmentation pipeline against physician annotations. We use strict subject-level splitting to prevent data leakage, but we treat it strictly as offline algorithmic verification, not a clinical validation of our physical hardware."*
* **Professor:** *"I see you switched microphones from PUI Audio to INMP441 in Week 04. Why was that change made, and who authorized it?"*
* **Candidate (Ege):** *"The change was documented in PR #28 by Ozan (Module B) during our Week 04 procurement closeout. Our initial BOM specified PUI Audio surface-mount MEMS microphones based on literature, but none of the Turkish local distributors (DirencNet, Robotistan, Özdisan) had them in stock. International shipping from DigiKey would have taken 4 weeks and risked university customs delays, preventing us from hitting our Week 05 bench bring-up gate. DirencNet had the INMP441 I2S MEMS breakout board in stock. Kaan (Module A) verified that its 61 dBA SNR and 24-bit I2S interface met our acoustic requirements for phantom testing, so we made the engineering substitution to keep the project on schedule."*
* **Professor:** *"What is the status of the six mandatory physical measurements?"*
* **Candidate (Ege):** *"Our software metrology pipeline in `pcg_core.metrology` is 100% written, verified with 394 passing tests, and ready. However, the physical measurements are officially classified as `HARDWARE_UNVERIFIED` / NOT YET MEASURED because our components were procured at the end of Week 04 and physical bench bring-up is scheduled for Week 05 in the laboratory. We refuse to present simulated numbers as physical measurements."*
* **Professor:** *"That is the exact scientific honesty we expect in senior design. Excellent defense."*
