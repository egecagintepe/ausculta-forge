# AuscultaForge — Engineering Knowledge Coverage Matrix

This matrix provides a comprehensive, bidirectional audit connecting academic curriculum requirements, subsystem architectures, scientific methods, verification targets, and historical milestones directly to their authoritative documentation artifacts and source code locations in the AuscultaForge repository.

---

## 1. Academic & Syllabus Knowledge Matrix (EEE495 / EEE496)

| Curriculum Area | Key Concept / Requirement | Primary Engineering Document | Source Code / Fixture Reference | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **Acoustic Transduction** | MEMS I2S microphone vs ECM analog conditioning | [ADR-0004](decisions/ADR-0004-i2s-digital-mems-vs-analog-ecm.md)<br>[PCG_SIGNAL_FOUNDATIONS](science/PCG_SIGNAL_FOUNDATIONS.md) | `docs/research/INMP441_MICROPHONE_ANALYSIS.md`<br>`docs/sdp/MODULE_A_ACOUSTIC_TRANSDUCTION.md` | `DOCUMENTED_PROPOSAL`<br>`HARDWARE_UNVERIFIED` |
| **Procurement Engineering** | Component substitution rationale (PUI to INMP441) | [ADR-0005](decisions/ADR-0005-inmp441-procurement-substitution.md)<br>[DEVELOPMENT_CHRONICLE](history/DEVELOPMENT_CHRONICLE.md) | `docs/research/PROCUREMENT_ALTERNATIVES_SUMMARY.md` | `GIT_VERIFIED` |
| **Embedded Architecture** | ESP32-S3 Xtensa LX7 dual-core, DMA, FreeRTOS | [ESP32_RUNTIME_ARCHITECTURE](code-atlas/ESP32_RUNTIME_ARCHITECTURE.md)<br>[ADR-0001](decisions/ADR-0001-esp32-s3-mcu-selection.md) | `tools/esp32_bench_example/main/main.c` | `CODE_VERIFIED` (C scaffold)<br>`HARDWARE_UNVERIFIED` |
| **Real-Time Data Buffering** | Producer-consumer ring buffers, FreeRTOS tasks | [BUFFERING_AND_REALTIME](code-atlas/BUFFERING_AND_REALTIME.md)<br>[RUNTIME_LIFECYCLE](architecture/RUNTIME_LIFECYCLE.md) | `software/pcg_app/stream_manager.py`<br>`software/pcg_core/buffers.py` | `CODE_VERIFIED`<br>`TEST_VERIFIED` (Host) |
| **Binary Serialization** | 24-bit PCM in S32_LE, two's-complement arithmetic | [PCM_BINARY_REPRESENTATION](code-atlas/PCM_BINARY_REPRESENTATION.md)<br>[C_LANGUAGE_FOUNDATIONS](code-atlas/C_LANGUAGE_FOUNDATIONS.md) | `software/pcg_app/device_runtime.py`<br>`tools/c_golden_vectors/golden_generator.c` | `CODE_VERIFIED`<br>`TEST_VERIFIED` |
| **Digital Communications** | USB CDC-ACM framing, packet synchronization | [USB_PROTOCOL_ENGINEERING](code-atlas/USB_PROTOCOL_ENGINEERING.md)<br>[ADR-0003](decisions/ADR-0003-usb-cdc-acm-transport.md) | `software/pcg_app/device_runtime.py`<br>`docs/protocol/USB_CDC_PACKET_FORMAT.md` | `CODE_VERIFIED`<br>`TEST_VERIFIED` |
| **Host System Architecture** | FastAPI asynchronous REST, WebSockets, background threads | [FASTAPI_API_REFERENCE](code-atlas/FASTAPI_API_REFERENCE.md)<br>[PYTHON_RUNTIME_WALKTHROUGH](code-atlas/PYTHON_RUNTIME_WALKTHROUGH.md) | `software/pcg_app/app.py`<br>`software/pcg_app/server.py` | `CODE_VERIFIED`<br>`TEST_VERIFIED` (394 pytest) |
| **Digital Signal Processing** | SOS Butterworth filtering, zero-phase vs causal | [DSP_MATHEMATICS](science/DSP_MATHEMATICS.md)<br>[ADR-0012](decisions/ADR-0012-host-python-dsp-vs-firmware-dsp.md) | `software/pcg_core/dsp.py` | `CODE_VERIFIED`<br>`TEST_VERIFIED` |
| **Spectral Analysis** | Welch PSD, STFT spectrogram, frequency binning | [SPECTRAL_ANALYSIS](science/SPECTRAL_ANALYSIS.md) | `software/pcg_core/scientific/spectral.py` | `CODE_VERIFIED`<br>`TEST_VERIFIED` |
| **System Identification** | Frequency response H1, coherence, latency estimation | [SYSTEM_IDENTIFICATION](science/SYSTEM_IDENTIFICATION.md) | `software/pcg_core/phantom.py` | `CODE_VERIFIED`<br>`TEST_VERIFIED` |
| **Segmentation Modeling** | Springer 4-state HMM/HSMM, duration modeling | [SEGMENTATION_MODELS](science/SEGMENTATION_MODELS.md) | `software/pcg_core/segmentation/` | `CODE_VERIFIED`<br>`TEST_VERIFIED` |
| **Measurement Uncertainty** | Type A/B uncertainty, GUM guidelines, noise floors | [MEASUREMENT_UNCERTAINTY](science/MEASUREMENT_UNCERTAINTY.md)<br>[ADR-0018](decisions/ADR-0018-engineering-metrology-vs-clinical-diagnosis.md) | `software/pcg_core/scientific/signal_quality.py` | `CODE_VERIFIED` |
| **Academic Defense** | Oral examination questions, failure fallback | [DEFENSE_HANDBOOK](defense/DEFENSE_HANDBOOK.md)<br>[QUESTION_BANK](defense/QUESTION_BANK.md) | Entire repository test suite & docs | `DOCUMENTED_PROPOSAL` |
| **Research Feasibility** | Deep learning extension roadmap, dataset provenance | [SEMESTER_II_AI_ROADMAP](research/SEMESTER_II_AI_ROADMAP.md)<br>[DEPENDENCY_AND_LICENSE_AUDIT](DEPENDENCY_AND_LICENSE_AUDIT.md) | `software/pcg_core/segmentation/` | `DOCUMENTED_PROPOSAL` |

---

## 2. Subsystem Functional Architecture Coverage

```
+---------------------------------------------------------------------------------------------------+
|                                       AUSCULTAFORGE SYSTEM                                        |
+-----------------------------------+-----------------------------------+---------------------------+
| Module A: Physical Acoustics      | Module B: Embedded Acquisition    | Module C: Host Software   |
| (Kaan)                            | (Ozan)                            | (Ege)                     |
+-----------------------------------+-----------------------------------+---------------------------+
| * Acoustic Stethoscope Head       | * INMP441 I2S Bus Configuration   | * DeviceRuntime Layer     |
| * Silicone / Agar Phantom         | * DMA Double-Buffering            | * StreamManager Routing   |
| * Transducer Mechanical Coupler   | * Packet Framing (16/40-byte)     | * Realtime DSP Engine     |
| * Transducer Evaluation           | * FreeRTOS Sample Generator       | * FastAPI & WebSockets    |
| * SPL & Acoustic Coupling         | * USB CDC-ACM Streaming           | * React Virtual Dashboard |
| [PCG_SIGNAL_FOUNDATIONS.md]       | [EMBEDDED_C_WALKTHROUGH.md]       | [PYTHON_RUNTIME_WALKTHROUGH] |
| [ADR-0004-i2s-vs-analog.md]       | [USB_PROTOCOL_ENGINEERING.md]     | [FASTAPI_API_REFERENCE.md]|
+-----------------------------------+-----------------------------------+---------------------------+
```

### Module A — Acoustic Transduction & Coupling (Lead: Kaan)
- **Acoustic Waveguide & Bell/Diaphragm Physics:** Documented in [PCG_SIGNAL_FOUNDATIONS](science/PCG_SIGNAL_FOUNDATIONS.md) §2 and [SYSTEM_IDENTIFICATION](science/SYSTEM_IDENTIFICATION.md) §4.
- **Microphone Selection & Procurement:** Traced in [ADR-0004](decisions/ADR-0004-i2s-digital-mems-vs-analog-ecm.md), [ADR-0005](decisions/ADR-0005-inmp441-procurement-substitution.md), and [DEVELOPMENT_CHRONICLE](history/DEVELOPMENT_CHRONICLE.md).
- **Physical Acoustic Phantom:** Detailed in [MEASUREMENT_UNCERTAINTY](science/MEASUREMENT_UNCERTAINTY.md) §6 and [SOFTWARE_VS_HARDWARE_EVIDENCE](verification/SOFTWARE_VS_HARDWARE_EVIDENCE.md) §4.
- **Hardware Status:** `HARDWARE_UNVERIFIED` — Pending laboratory test bench assembly and calibrated phantom excitation.

### Module B — Embedded Acquisition & Transmit (Lead: Ozan)
- **ESP32-S3 Dual-Core Architecture:** Documented in [ESP32_RUNTIME_ARCHITECTURE](code-atlas/ESP32_RUNTIME_ARCHITECTURE.md).
- **C Language Bitwise & Two's Complement:** Documented in [C_LANGUAGE_FOUNDATIONS](code-atlas/C_LANGUAGE_FOUNDATIONS.md) and [PCM_BINARY_REPRESENTATION](code-atlas/PCM_BINARY_REPRESENTATION.md).
- **FreeRTOS Real-Time Tasks & Ring Buffers:** Documented in [BUFFERING_AND_REALTIME](code-atlas/BUFFERING_AND_REALTIME.md).
- **USB CDC-ACM Packet Protocol & Framing:** Documented in [USB_PROTOCOL_ENGINEERING](code-atlas/USB_PROTOCOL_ENGINEERING.md) and [ADR-0003](decisions/ADR-0003-usb-cdc-acm-transport.md).
- **Experimental Sample Generator:** Source in `tools/esp32_bench_example/main/main.c`, audited in [EMBEDDED_C_WALKTHROUGH](code-atlas/EMBEDDED_C_WALKTHROUGH.md). Status: `HARDWARE_UNVERIFIED`.

### Module C — Host Software, DSP & User Interface (Lead: Ege)
- **Device Runtime & Transport Management:** Documented in [PYTHON_RUNTIME_WALKTHROUGH](code-atlas/PYTHON_RUNTIME_WALKTHROUGH.md) §2 (`software/pcg_app/device_runtime.py`).
- **Stream Routing & Display Decimation:** Documented in [PYTHON_RUNTIME_WALKTHROUGH](code-atlas/PYTHON_RUNTIME_WALKTHROUGH.md) §3 (`software/pcg_app/stream_manager.py`).
- **Signal Processing & Filtering:** Documented in [DSP_MATHEMATICS](science/DSP_MATHEMATICS.md) (`software/pcg_core/dsp.py`).
- **Spectral & System Identification:** Documented in [SPECTRAL_ANALYSIS](science/SPECTRAL_ANALYSIS.md) and [SYSTEM_IDENTIFICATION](science/SYSTEM_IDENTIFICATION.md) (`software/pcg_core/scientific/` and `software/pcg_core/phantom.py`).
- **Segmentation Modeling:** Documented in [SEGMENTATION_MODELS](science/SEGMENTATION_MODELS.md) (`software/pcg_core/segmentation/`).
- **FastAPI HTTP & WebSocket Interface:** Documented in [FASTAPI_API_REFERENCE](code-atlas/FASTAPI_API_REFERENCE.md) (`software/pcg_app/app.py`).
- **Audio Session Persistence & WAV Export:** Documented in [RECORDING_AND_SESSION_INTERNALS](code-atlas/RECORDING_AND_SESSION_INTERNALS.md) (`software/pcg_core/recording.py`).
- **React Frontend Dashboard:** Documented in [FRONTEND_ARCHITECTURE](code-atlas/FRONTEND_ARCHITECTURE.md) (`software/frontend/`).
- **Cross-Language Contracts:** Documented in [CROSS_LANGUAGE_DATA_CONTRACTS](code-atlas/CROSS_LANGUAGE_DATA_CONTRACTS.md).

---

## 3. Verification & Evidence Cross-Reference

| Verification Class | Scope & Mechanism | Primary Reference Document | Evidence File / Command | Observed Result |
| :--- | :--- | :--- | :--- | :--- |
| **Python Automated Tests** | Unit, pipeline, API, and mock streaming | [TEST_ATLAS](verification/TEST_ATLAS.md) | `pytest` | 394 passed, 1 warning (16.42s) |
| **Frontend TypeScript** | Strict type safety and compilation | [REPRODUCIBILITY_GUIDE](verification/REPRODUCIBILITY_GUIDE.md) | `npm run lint` / `tsc --noEmit` | 0 errors |
| **Frontend Unit Tests** | Decimation, display math, telemetry | [TEST_ATLAS](verification/TEST_ATLAS.md) | `npm run test` (Vitest) | 4 passed |
| **Frontend Production Build**| Vite bundle optimization and asset packaging | [FRONTEND_ARCHITECTURE](code-atlas/FRONTEND_ARCHITECTURE.md) | `npm run build` | Clean build in 3.48s |
| **Portable C Bench Parity** | Golden vector bit-exactness between C & Python | [TEST_ATLAS](verification/TEST_ATLAS.md) | `tools/c_golden_vectors/` | 6/6 tests passed |
| **Requirements Traceability**| PR #18–31 functional compliance mapping | [REQUIREMENTS_TRACEABILITY](verification/REQUIREMENTS_TRACEABILITY.md) | Multi-module review | 100% software requirements mapped |
| **Hardware Bringup Checks** | ESP32-S3 UART/CDC connection and polling | [SOFTWARE_VS_HARDWARE_EVIDENCE](verification/SOFTWARE_VS_HARDWARE_EVIDENCE.md) | `docs/hardware/ESP32_S3_BRINGUP_CHECKLIST.md` | `HARDWARE_UNVERIFIED` (Requires physical bench) |

---

## 4. Architecture Decision Records (ADR) Summary

| ADR ID | Title | Status | Primary Driver |
| :--- | :--- | :--- | :--- |
| **ADR-0001** | [ESP32-S3 MCU Selection](decisions/ADR-0001-esp32-s3-mcu-selection.md) | Accepted | Dual-core, native USB Full-Speed OTG, dual I2S peripherals |
| **ADR-0002** | [Wired USB vs Wireless Transport](decisions/ADR-0002-wired-native-usb-vs-wireless.md) | Accepted | Packet loss avoidance, deterministic latency, electrical safety |
| **ADR-0003** | [USB CDC-ACM Transport Protocol](decisions/ADR-0003-usb-cdc-acm-transport.md) | Accepted | Driverless OS integration, cross-platform serial emulation |
| **ADR-0004** | [I2S MEMS vs Analog ECM Acquisition](decisions/ADR-0004-i2s-digital-mems-vs-analog-ecm.md) | Accepted | In-package 24-bit ADC, immunity to analog EMI/cable crosstalk |
| **ADR-0005** | [INMP441 Procurement Substitution](decisions/ADR-0005-inmp441-procurement-substitution.md) | Accepted | Supply chain availability, breakout board form factor |
| **ADR-0006** | [Nominal 48 kHz Sampling Baseline](decisions/ADR-0006-nominal-48khz-sampling-baseline.md) | Accepted | High acoustic oversampling, standard audio clock compliance |
| **ADR-0007** | [S32_LE PCM Container Format](decisions/ADR-0007-s32-le-pcm-container-format.md) | Accepted | Direct 32-bit slot packing from 24-bit MSB-justified I2S |
| **ADR-0008** | [Packet Framing & Header Evolution](decisions/ADR-0008-packet-framing-and-header-evolution.md) | Accepted | Magic bytes, session IDs, monotonic sequence counters |
| **ADR-0009** | [Monotonic Sample Counter Policy](decisions/ADR-0009-monotonic-sample-counter-policy.md) | Accepted | Cumulative sample index enables absolute packet drop detection |
| **ADR-0010** | [Hardware Timestamps vs Host Timebase](decisions/ADR-0010-hardware-timestamps-vs-host-timebase.md) | Accepted | Microsecond hardware timer decoupled from USB jitter |
| **ADR-0011** | [CRC Integrity Verification Policy](decisions/ADR-0011-crc-integrity-verification-policy.md) | Accepted | End-to-end payload bit-error detection over serial bridge |
| **ADR-0012** | [Host Python DSP vs Firmware DSP](decisions/ADR-0012-host-python-dsp-vs-firmware-dsp.md) | Accepted | Double-precision scientific algorithms, rapid research iteration |
| **ADR-0013** | [FastAPI REST & WebSocket Architecture](decisions/ADR-0013-fastapi-rest-and-websocket-architecture.md) | Accepted | Decoupled client-server model, low-overhead binary streaming |
| **ADR-0014** | [Lossless Raw WAV & Metadata Sidecar](decisions/ADR-0014-lossless-raw-wav-and-metadata-sidecar.md) | Accepted | 24-bit raw PCM preservation with SHA-256 integrity hash |
| **ADR-0015** | [Bounded Display Decimation](decisions/ADR-0015-bounded-peak-preserving-display-decimation.md) | Accepted | Min/Max envelope preserves acoustic spikes without UI lag |
| **ADR-0016** | [Separation of Scientific DSP and UI](decisions/ADR-0016-separation-of-scientific-dsp-and-ui.md) | Accepted | Clean boundary between computational analytics and React canvas |
| **ADR-0017** | [Virtual Bench & Golden Vectors](decisions/ADR-0017-virtual-bench-and-golden-vector-verification.md) | Accepted | Fully reproducible software testing independent of hardware |
| **ADR-0018** | [Engineering Metrology vs Clinical Scope](decisions/ADR-0018-engineering-metrology-vs-clinical-diagnosis.md) | Accepted | Strict non-diagnostic acoustic quality and verification scope |

---

## 5. Maintenance and Governance

This matrix is governed under the maintenance guidelines set forth in [DOCUMENTATION_MAINTENANCE](DOCUMENTATION_MAINTENANCE.md). Any pull request altering routes, data models, signal processing algorithms, or hardware interfaces must update this coverage matrix concurrently.
