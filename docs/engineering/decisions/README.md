# AuscultaForge — Architectural Decision Record (ADR) Catalog
**Catalog ID:** `AF-ADR-CATALOG-V01`  
**Classification:** `GIT_VERIFIED` / `CODE_VERIFIED`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Baseline Git Commit:** `fa4b75a80d29aab04875534234574db9f6c0af43`

---

## 1. Overview and Governance

Architectural Decision Records (ADRs) capture significant architectural and technical choices made throughout the AuscultaForge lifecycle. Every record documents the engineering context, alternatives considered, decision rationale, status, trade-offs, and verification evidence.

### Status Classification:
* `ACCEPTED`: Fully approved, integrated into master codebase, and verified by tests.
* `PROPOSED`: Specified in technical documentation, but awaiting formal joint sign-off or physical hardware testing.
* `REJECTED`: Considered and formally eliminated based on technical or procurement constraints.
* `SUPERSEDED`: Replaced by a subsequent architectural decision.

---

## 2. Master Decision Index (ADR-0001 through ADR-0018)

| ADR ID | Decision Title | Status | Primary Owner | Affected Subsystem | Key Trade-Off / Rationale |
|---|---|---|---|---|---|
| **[ADR-0001](ADR-0001-esp32-s3-mcu-selection.md)** | ESP32-S3 Microcontroller Selection | `ACCEPTED` | Module B / C | `firmware/`, `hardware/` | Dual Xtensa cores, native USB OTG PHY, and I2S DMA. |
| **[ADR-0002](ADR-0002-wired-native-usb-vs-wireless.md)** | Wired Native USB vs. Wireless Transport | `ACCEPTED` | Module B / C | `firmware/`, `software/` | Eliminates RF packet drops, 2.4 GHz interference, and latency jitter. |
| **[ADR-0003](ADR-0003-usb-cdc-acm-transport.md)** | USB CDC-ACM Class Selection | `ACCEPTED` | Module B / C | `software/pcg_app/` | Zero-driver footprint on Windows (`usbser.sys`). |
| **[ADR-0004](ADR-0004-i2s-digital-mems-vs-analog-ecm.md)** | I2S Digital MEMS vs. Analogue ECM Baseline | `ACCEPTED` | Module A | `hardware/` | Digital MEMS bypasses breadboard analog noise and pre-amp design. |
| **[ADR-0005](ADR-0005-inmp441-procurement-substitution.md)** | INMP441 Sourcing Substitution (Replaces PUI) | `ACCEPTED` | Module B / A | `hardware/`, BOM | Turkish distributor availability; PUI unavailable locally. |
| **[ADR-0006](ADR-0006-nominal-48khz-sampling-baseline.md)** | Nominal 48 kHz Sampling Rate Baseline | `ACCEPTED` | Module B / C | `firmware/`, `software/` | Standard I2S clock dividers ($3.072\text{ MHz}$ BCLK); 48x oversampling. |
| **[ADR-0007](ADR-0007-s32-le-pcm-container-format.md)** | S32_LE Container Format for 24-bit Audio | `ACCEPTED` | Module B / C | `software/`, `tools/` | 32-bit aligned memory words; explicit sign extension logic. |
| **[ADR-0008](ADR-0008-packet-framing-and-header-evolution.md)** | 40-byte Packet Framing vs. Bulk Stream | `PROPOSED` | Module B | `docs/protocol/` | Fixed 40-byte frame with CRC vs. raw continuous blocks. |
| **[ADR-0009](ADR-0009-monotonic-sample-counter-policy.md)** | Monotonic Cumulative Sample Counter Policy | `ACCEPTED` | Module B / C | `software/pcg_core/` | Tracks absolute sample continuity and drops across wraparounds. |
| **[ADR-0010](ADR-0010-hardware-timestamps-vs-host-timebase.md)** | Hardware MCU Ticks vs. Host Arrival Timebase | `ACCEPTED` | Module C | `software/pcg_app/` | Host monotonic timebase for files; MCU ticks for jitter analysis. |
| **[ADR-0011](ADR-0011-crc-integrity-verification-policy.md)** | CRC-16 Wire Check & SHA-256 File Check Policy | `ACCEPTED` | Module C | `software/pcg_core/` | CRC-16 for wire frames; SHA-256 for persistent session sidecars. |
| **[ADR-0012](ADR-0012-host-python-dsp-vs-firmware-dsp.md)** | Host Python DSP vs. Embedded Firmware DSP | `ACCEPTED` | Module C | `software/pcg_core/` | Preserves raw unprocessed sensor data; host CPU has double precision. |
| **[ADR-0013](ADR-0013-fastapi-rest-and-websocket-architecture.md)**| FastAPI Factory Pattern & WebSocket Architecture| `ACCEPTED` | Module C | `software/pcg_app/` | Async non-blocking loop; 57 registered endpoints; clean factory. |
| **[ADR-0014](ADR-0014-lossless-raw-wav-and-metadata-sidecar.md)** | Lossless Raw WAV Audio + JSON Metadata Sidecar | `ACCEPTED` | Module C | `software/pcg_core/` | Verifiable provenance, Git commit SHA, and zero data alteration. |
| **[ADR-0015](ADR-0015-bounded-peak-preserving-display-decimation.md)**| Bounded Peak-Preserving Display Decimation | `ACCEPTED` | Module C | `software/pcg_app/` | Min/max decimation ($\le 600$ pts) protects 60 FPS canvas loop. |
| **[ADR-0016](ADR-0016-separation-of-scientific-dsp-and-ui.md)**| Strict Decoupling of Scientific DSP from UI | `ACCEPTED` | Module C | `software/` | `pcg_core` has zero UI/web dependencies; executes in headless CI. |
| **[ADR-0017](ADR-0017-virtual-bench-and-golden-vector-verification.md)**| Virtual Bench & C Golden Vector Verification | `ACCEPTED` | Module C | `software/`, `tools/` | Deterministic verification prior to physical hardware delivery. |
| **[ADR-0018](ADR-0018-engineering-metrology-vs-clinical-diagnosis.md)**| Technical Metrology vs. Clinical Diagnosis | `ACCEPTED` | Academic Scope | All Subsystems | Formal academic boundary: engineering acoustic metrology only. |
