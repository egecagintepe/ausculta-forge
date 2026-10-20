# AuscultaForge — Complete System Architecture Reference
**Document ID:** `AF-ARCH-SYSTEM-V01`  
**Classification:** `CODE_VERIFIED` / `DOCUMENTED_PROPOSAL`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Baseline Git Commit:** `fa4b75a80d29aab04875534234574db9f6c0af43`  
**Primary Author:** Ege Çağın Tepe (Module C Owner)

---

## 1. High-Level Architectural Vision

AuscultaForge implements an end-to-end digital phonocardiography (PCG) acquisition and metrology pipeline. The system acquires faint heart sounds ($20\text{--}500\text{ Hz}$) from an acoustic test phantom or chestpiece, digitizes the signal via an integrated I2S MEMS transducer, transfers binary frames over a high-throughput wired USB transport, and performs real-time DSP, cryptographic recording, and scientific system identification on a host PC.

```mermaid
graph TB
    subgraph PHYSICAL_LAYER ["Layer 0: Physical & Acoustic Front-End"]
        PHANTOM["Acoustic Test Phantom<br>(Audio Exciter + Silicone Layer)"] --> CHESTPIECE["Acoustic Chestpiece<br>(Bell / Diaphragm Cavity)"]
        CHESTPIECE --> MIC_I2S["Primary: INMP441 I2S MEMS<br>(24-bit Sigma-Delta ADC)"]
        CHESTPIECE -.-> MIC_ECM["Secondary: Electret Condenser<br>(Analog Pre-amp + Sallen-Key)"]
    end

    subgraph EMBEDDED_LAYER ["Layer 1: Embedded Microcontroller (ESP32-S3)"]
        MIC_I2S -->|BCLK: 3.072 MHz<br>WS: 48 kHz<br>SD: 24-bit PCM| I2S_DMA["Hardware I2S DMA Controller<br>(Double-Buffered Ring Descriptors)"]
        I2S_DMA --> RTOS_TASK["Acquisition Task<br>(Sequence Counter & Framing)"]
        RTOS_TASK --> USB_FIFO["TinyUSB CDC-ACM FIFO Queue<br>(Backpressure & Drop Accounting)"]
    end

    subgraph TRANSPORT_LAYER ["Layer 2: Physical Interconnect"]
        USB_FIFO -->|Full-Speed USB 2.0 (12 Mbps)<br>CDC-ACM Serial Bulk Packets| USB_CABLE["Shielded USB Cable<br>(D+, D-, VBUS, GND)"]
    end

    subgraph HOST_BACKEND ["Layer 3: Python Host Runtime & DSP Engine"]
        USB_CABLE --> HOST_TRANS["Host Transport Layer<br>(Layer 1 Byte Stream Reader)"]
        HOST_TRANS --> FRAME_DEC["Layer 2: Frame Decoder & CRC-16 Check"]
        FRAME_DEC --> SAMPLE_NORM["Layer 3: Sample Normalizer & Unpacker<br>(S32_LE -> Float64 [-1.0, +1.0])"]
        SAMPLE_NORM --> STREAM_MGR["StreamManager & DeviceRuntime<br>(Authoritative State Machine)"]
        
        STREAM_MGR --> RECORDER["Lossless Session Recorder<br>(48 kHz 24-bit WAV + JSON Sidecar)"]
        STREAM_MGR --> DSP_PIPE["Stateful Bandpass Filter<br>(20-500 Hz SOS Filter)"]
        STREAM_MGR --> DECIMATOR["DisplayDecimator Pipeline<br>(Peak-Preserving <= 600 min/max points)"]
        STREAM_MGR --> METROLOGY["Scientific Metrology & System ID<br>(Welch PSD, SISO H1, Coherence)"]
    end

    subgraph USER_INTERFACE ["Layer 4: Desktop Application (React / TypeScript)"]
        DECIMATOR -->|WebSocket: 30-60 Hz Frames| WS_CLIENT["BridgeClient.ts (Typed WebSocket)"]
        METROLOGY -->|REST API: JSON Endpoints| REST_CLIENT["API Client (Axios / Fetch)"]
        
        WS_CLIENT --> CANVAS_UI["Live Workstation Canvas<br>(Circular Rolling Waveform)"]
        REST_CLIENT --> LAB_UI["ScientificLab & Metrology Lab<br>(PSD Plots, H1 Curves, Reports)"]
    end
```

---

## 2. Quantitative Dataflow & Bandwidth Budget

To ensure zero sample loss across the entire system, the communication interfaces and buffer queues are sized with substantial bandwidth margins:

### 2.1 I2S Bus Physical Timing
* **Sampling Rate ($f_s$):** $48,000 \text{ Hz}$ ($48.000 \text{ kHz}$)
* **Channels ($N_{ch}$):** 2 channel slots (Standard I2S frame format: Left + Right slot). INMP441 transmits on Left channel (`L/R` tied to GND); Right channel is tri-stated / zeroed.
* **Bits per Slot ($N_{bits}$):** 32 clock cycles per slot (24 audio bits with 8 padding bits).
* **Continuous Bit Clock Frequency ($f_{\text{SCK}}$):**
  $$f_{\text{SCK}} = 2 \times N_{bits} \times f_s = 2 \times 32 \times 48,000 = 3,072,000 \text{ Hz} = 3.072 \text{ MHz}$$
* **Word Select Frequency ($f_{\text{WS}}$):**
  $$f_{\text{WS}} = f_s = 48,000 \text{ Hz}$$
* **Raw Audio Bitrate from Sensor:**
  $$\text{Bitrate}_{\text{I2S}} = 1 \text{ channel} \times 24 \text{ bits} \times 48,000 \text{ Hz} = 1.152 \text{ Mbps}$$

### 2.2 USB CDC-ACM Transport Budget
* **Container Word Size:** 32-bit signed integer (`int32_t`, `S32_LE`).
* **Frame Payload:** 512 samples per transmission block ($\Delta t = 512 / 48000 \approx 10.667 \text{ ms}$).
* **Payload Size per Block:**
  $$S_{\text{payload}} = 512 \text{ samples} \times 4 \text{ bytes/sample} = 2,048 \text{ bytes}$$
* **Framing Overhead (Proposed 40-byte Packet Framing):**
  * If transmitting in raw blocks: $2,048 \text{ bytes} \times 93.75 \text{ blocks/s} = 192,000 \text{ bytes/s} = 1.536 \text{ Mbps}$.
  * If transmitting in 40-byte packets (8 samples = 32 bytes payload + 8 bytes header/CRC):
    $$\text{Packet Rate} = 48,000 / 8 = 6,000 \text{ packets/s}$$
    $$\text{Data Rate} = 6,000 \times 40 \text{ bytes} = 240,000 \text{ bytes/s} = 1.92 \text{ Mbps}$$
* **Physical USB Bandwidth Margin:**
  * USB 2.0 Full-Speed gross signaling rate is $12.000 \text{ Mbps}$.
  * Practical sustained CDC-ACM bulk throughput is $\approx 8.0 \text{--} 9.5 \text{ Mbps}$.
  * Bus utilization is $\le 20\%$, providing an $80\%$ headroom margin against USB host polling latency.

---

## 3. Subsystem Architectural Breakdown

### 3.1 Transducer & Front-End Interface (Module A)
The front-end design accommodates two mutually exclusive transducer topologies:
1. **Primary Baseline — INMP441 Digital MEMS:**
   * Bottom-port omnidirectional acoustic sensor.
   * Internal acoustic transducer bonded to CMOS signal conditioning and 24-bit multi-bit $\Sigma\Delta$ ADC.
   * High-pass acoustic corner at $\approx 10 \text{ Hz}$, flat response across $20\text{--}500 \text{ Hz}$.
   * Acoustic Sensitivity: $-26 \text{ dBFS} \pm 3 \text{ dB}$ at $1 \text{ kHz}, 94 \text{ dB SPL}$.
   * SNR: $61 \text{ dBA}$.
2. **Secondary Alternative — Electret Condenser Microphone (ECM):**
   * High-sensitivity condenser capsule with internal JFET impedance converter.
   * External hardware conditioning: Low-noise active bandpass filter (2nd-order Sallen-Key, passband $20\text{--}500 \text{ Hz}$, gain $A_v \approx 40 \text{ dB}$).
   * Input to ESP32-S3 internal 12-bit SAR ADC (`ADC1_CH4` / `GPIO 5`).

### 3.2 Microcontroller Acquisition Architecture (Module B)
* **ESP32-S3 Processing Cores:**
  * **Core 0 (Protocol & Transport):** Handles TinyUSB CDC-ACM stack, USB endpoint interrupts, and packet serialization.
  * **Core 1 (Real-Time Acquisition):** Owns I2S DMA interrupt servicing, ring buffer management, and sample continuity sequencing.
* **DMA Double-Buffering:**
  * Uses linked-list DMA descriptors (`lldesc_t`) configured in ping-pong mode.
  * When Buffer A is being filled by hardware I2S DMA, Buffer B is copied into the FreeRTOS stream queue without disabling interrupts.

### 3.3 Host Application Architecture (Module C)
The Python application (`pcg_app`) is structured around an asynchronous, non-blocking service model:
* **`pcg_app.device_runtime.DeviceRuntime`:**
  * Authoritative singleton maintaining the hardware lifecycle.
  * Transitions deterministically between 8 states:
    $$\text{ABSENT} \leftrightarrow \text{DETECTED} \leftrightarrow \text{OPENING} \leftrightarrow \text{HANDSHAKING} \leftrightarrow \text{READY} \leftrightarrow \text{STREAMING} \leftrightarrow \text{CLOSING} \leftrightarrow \text{INTERRUPTED}$$
* **`pcg_app.state.StreamManager`:**
  * Directs incoming sample streams from physical USB serial, deterministic `VirtualBench`, or recorded WAV sources to connected listeners.
  * Maintains an in-memory `RollingBuffer` holding the latest 5.0 seconds of audio for instant display and spectral analysis.
* **`pcg_app.display_pipeline.DisplayDecimator`:**
  * Compresses raw 48 kHz blocks into bounded $(\le 600)$ point min/max vectors, protecting the React WebSocket thread from buffer saturation.
* **`pcg_core.recording.SessionRecorder`:**
  * Writes streaming audio directly to an uncompressed 24-bit PCM WAV file.
  * Simultaneously computes a running SHA-256 hash of all written PCM sample bytes, serializing the final hash and drop metrics into an immutable JSON sidecar on session close.

---

## 4. Cross-Module Boundaries & Responsibilities

| Subsystem | Primary Owner | Code Repository Location | Key Output Artifacts |
|---|---|---|---|
| **Acoustic Transducer & Chestpiece** | **Kaan (Module A)** | `hardware/` | Schematics, 3D Chestpiece CAD, Phantom Test Matrix |
| **Microcontroller Firmware & USB Stack** | **Ozan (Module B)** | `firmware/` | ESP-IDF Firmware, I2S DMA Drivers, Packet Framing |
| **Desktop Bridge & DSP Metrology** | **Ege (Module C)** | `software/`, `tools/` | FastAPI Bridge, React UI, Metrology Automation, Tests |
