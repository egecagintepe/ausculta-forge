# W05 Module C — Host Integration Preflight & Acceptance Readiness (v01)

> **Current-status addendum — 2026-10-26 (documentation review, baseline `106d3e0`):** **New physical CLI G1 PASS verified on 2026-10-26 at 07:50 UTC**, host `106d3e0`, COM7 / VID:PID `303A:4001`, firmware `1.1.0`, protocol `1.0`: 480000 accepted samples, 1875 frames, zero integrity errors and STOP_ACK. Local original evidence: `experiments/hardware/week6_20261026_sprint/cli-g1/20261026T075048Z_f26df565/g1_protocol_summary.json`. The earlier laptop run remains user-reported; this is a separate new mini PC run. GUI physical G1 **PASS at 59d773e** on 2026-10-26 08:14 UTC; final e90785e GUI HELLO/READY/disconnect **PASS**, full G1 repeat **NOT_EXECUTED (two-start limit)**. Real microphone G2 remains **PENDING**. See the [sprint report](../../../../engineering/release/WEEK6_SPRINT_REPORT.md). See the [current closeout and missing-evidence register](W05_C_live-display-recording-verification.md).
>
> The body below is a **historical snapshot**, including its status fields, proposals, implementation descriptions and test outputs; none was rerun today. Statements about hardware arrival, pending USB/decoder implementation or untested G1 describe that earlier baseline, not the current checkout. Canonical host code now exists in `software/pcg_app/canonical/`; implementation does not prove joint Module B sign-off or microphone qualification.


**Course:** EEE495 — Senior Design Project I  
**Week:** 05 Preflight — Sprint 1  
**Module:** C — Computer Application & Quality Assessment  
**Author:** Ege Çağın Tepe (Module C Owner)  
**Status:** HOST PREFLIGHT COMPLETE / PHYSICAL HARDWARE INTEGRATION PENDING  
**Scope:** Host software known-answer verification, test suite execution, and acceptance test mapping. No physical hardware connection or MCU bench measurements are simulated or claimed.

---

## 1. Executive Summary & Gate Status

This deliverable establishes the host-side readiness of AuscultaForge for the upcoming Week 05 integration with the physical ESP32-S3 Native USB streaming pipeline.

### Gate G1 Status:
- **Gate G1 Definition:** Physical MCU-to-PC data link validation over wired ESP32-S3 Native USB.
- **Current Status:** **PENDING / NOT TESTED ON HARDWARE**.
- **Declaration:** Gate G1 is **NOT MARKED PASSED**. The production host application truthfully reports discovery status as pending (`PendingDescriptorDiscoveryProvider`) and refuses to simulate physical USB hardware in production. All preflight tests are strictly labeled `SOFTWARE_KNOWN_ANSWER`.

---

## 2. Phase 1 — Repository Audit & Baseline Assessment

A comprehensive inspection of the software and architectural documentation was conducted:

| Repository Subsystem | File Inspected | Current Implementation State | Preflight Audit Findings |
|---|---|---|---|
| **Device Runtime** | `software/pcg_app/device_runtime.py` | Full 9-state lifecycle machine (`DeviceRuntime`), `AcquisitionProfile` model, strict capability validation, `DeviceSamplePacket` representation, integer-to-float adapter (`packet_to_sample_block`), and `DeviceIntegrityStats`. | Core runtime foundation was complete and robust. Decoders are properly abstracted (`DevicePacketDecoder`) pending byte-level protocol freeze. |
| **Stream Management** | `software/pcg_app/state.py` | `StreamManager` with push-driven hardware ingestion entry point (`ingest_device_packet`), DSP pipeline dispatch, recording coordination, and client broadcasting. | Fully supports 48 kHz push ingestion. Correctly drops CRC-failed frames, records full-rate uncorrupted WAV, and tracks telemetry. |
| **Session Provenance** | `software/pcg_core/recording.py` | `SessionRecorder`, `SessionMetadata`, `raw.wav` float32 serializer, sidecar JSON writer, and SHA-256 hash computation. | Verified path traversal protection, clean error abort handling, and metadata consistency. |
| **Stream Health** | `software/pcg_core/streaming.py` | `StreamQualityMonitor`, `QualityReport`, `LiveStreamingPipeline`. | Monitors dropped blocks, repeated sequences, sequence gaps, and timestamp regressions dynamically. |
| **API & App Bridge** | `software/pcg_app/app.py` | FastAPI REST & WebSocket endpoints (`/api/status`, `/api/device/state`, `/api/device/events`, `/api/device/stats`). | Endpoints truthfully expose runtime state, active acquisition profile, and device telemetry. |
| **Existing Tests** | `software/tests/test_device_runtime.py` | 27 automated unit tests covering state machine transitions, handshake capability validation, and basic packet conversion. | Multi-block continuous synthetic preservation, spectral fidelity, and full hash verification were not previously grouped in an end-to-end preflight suite. |

---

## 3. Phase 2 — Host Preflight Testing & Verification Results

A dedicated, deterministic preflight verification suite (`TestHostPreflightVerification`) was implemented in `software/tests/test_device_runtime.py` without modifying production hardware discovery or introducing fake USB drivers.

### 3.1 Verification Priorities Summary

| Priority | Test Name | Ingestion Stimulus | Verified Behavior | Result Label | Status |
|---|---|---|---|---|---|
| **1. 48 kHz Signal Preservation** | `test_known_48khz_mono_synthetic_signal_preservation` | 10 blocks (5120 samples) of pure 100 Hz sine wave at 48 kHz, 24-bit in 32-bit container | Recorded float32 WAV matches original sine wave with maximum error $< 10^{-4}$. Welch PSD confirms peak frequency at exactly 100.0 Hz. | `SOFTWARE_KNOWN_ANSWER` | **PASS** |
| **2. Signed Normalization** | `test_signed_integer_conversion_and_normalization_ranges` | Min legal, half-scale, zero, quarter-scale, max legal across 24-bit and 16-bit depths | Normalized float32 accurately scales to $[-1.0, +1.0]$. Out-of-range integers raise explicit `ValueError` without clipping. | `SOFTWARE_KNOWN_ANSWER` | **PASS** |
| **3. Sample Ordering Across Blocks** | `test_multi_block_sample_ordering_and_continuity_across_boundaries` | 8 blocks (4096 samples) of strictly monotonic counter integers | Monotonic sample order preserved across block boundaries (e.g. index 511→512, 1023→1024). Exact sample count (4096) recorded. | `SOFTWARE_KNOWN_ANSWER` | **PASS** |
| **4. Gap & Duplicate Detection** | `test_stream_ingest_duplicate_and_gap_telemetry_detection` | Sequence: 0, 0 (duplicate), 1, 4 (gap of 2) | Telemetry tracks `repeated_packets == 1`, `sequence_gaps == 2`. Quality report flags `is_healthy == False`. | `SOFTWARE_KNOWN_ANSWER` | **PASS** |
| **5. WAV & JSON Hash Integrity** | `test_wav_json_integrity_and_sha256_verification` | 3 blocks (1536 samples) with active hardware session | `raw_wav_sha256` in `session.json` exactly matches SHA-256 computed from `raw.wav` on disk. Session metadata verified. | `SOFTWARE_KNOWN_ANSWER` | **PASS** |
| **6. Disconnect Safe Finalization** | `test_safe_recording_finalization_after_device_interruption` | 2 blocks (1024 samples) ingested, followed by abrupt disconnect | Recording halted cleanly. `session.json` records `termination_reason='device_disconnected'`. Intact 1024-sample WAV preserved. | `SOFTWARE_KNOWN_ANSWER` | **PASS** |
| **7. Unsupported Profile Rejection** | `test_unsupported_acquisition_profile_rejection_at_handshake` | Incompatible protocol ("9.9"), sample rate (44.1 kHz), container width (16-bit) | Runtime raises `ValueError`, transitions to `DeviceState.INCOMPATIBLE`, logs `HANDSHAKE_REJECTED`, resets cleanly to `ABSENT`. | `SOFTWARE_KNOWN_ANSWER` | **PASS** |

### 3.2 Actual Test Execution Output

Targeted Module C Preflight Suite (`software/tests/test_device_runtime.py`):
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Dev\Antigravity\bitirme\ausculta-forge
configfile: pytest.ini
plugins: anyio-4.15.1
collected 34 items

software\tests\test_device_runtime.py .................................. [100%]

============================= 34 passed in 2.10s ==============================
```

Complete Repository Suite Execution (`pytest software/tests`):
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Dev\Antigravity\bitirme\ausculta-forge
configfile: pytest.ini
testpaths: software/tests
plugins: anyio-4.15.1
collected 281 items

software\tests\test_analysis.py .......                                  [  2%]
software\tests\test_analysis_service.py ..................               [  8%]
software\tests\test_app.py ........                                      [ 11%]
software\tests\test_cinc2016_adapter.py ...                              [ 12%]
software\tests\test_circor_adapter.py ........                           [ 15%]
software\tests\test_core.py ..                                           [ 16%]
software\tests\test_device_runtime.py .................................. [ 28%]
software\tests\test_display_pipeline.py ...........                      [ 32%]
software\tests\test_experiment.py .........                              [ 35%]
software\tests\test_recording.py .......                                 [ 38%]
software\tests\test_scientific_api.py .......                            [ 40%]
software\tests\test_scientific_config.py ......................          [ 48%]
software\tests\test_scientific_envelopes.py ........                     [ 51%]
software\tests\test_scientific_signal_quality.py ...........             [ 55%]
software\tests\test_scientific_spectral.py ...........                   [ 59%]
software\tests\test_scientific_system_id.py ........                     [ 61%]
software\tests\test_springer_api.py ....                                 [ 63%]
software\tests\test_springer_durations.py ....                           [ 64%]
software\tests\test_springer_end_to_end.py .....                         [ 66%]
software\tests\test_springer_evaluation.py ...                           [ 67%]
software\tests\test_springer_features.py ...........                     [ 71%]
software\tests\test_springer_heart_rate.py ...........                   [ 75%]
software\tests\test_springer_hsmm.py ......                              [ 77%]
software\tests\test_springer_logistic.py .....                           [ 79%]
software\tests\test_springer_preprocessing.py ............               [ 83%]
software\tests\test_springer_training_labels.py ....                     [ 85%]
software\tests\test_streaming.py .........                               [ 88%]
software\tests\test_validation.py ..........                             [ 91%]
software\tests\test_validation_annotations_mask.py .....                 [ 93%]
software\tests\test_validation_api.py .                                  [ 93%]
software\tests\test_validation_end_to_end_synthetic.py ..                [ 94%]
software\tests\test_validation_failure_inclusive.py .                    [ 95%]
software\tests\test_validation_macro_subject.py .                        [ 95%]
software\tests\test_validation_matching.py ........                      [ 98%]
software\tests\test_validation_metrics.py .                              [ 98%]
software\tests\test_validation_splitting_leakage.py ...                  [ 99%]
software\tests\test_validation_state_metrics.py .                        [100%]

======================= 281 passed, 1 warning in 6.95s ========================
```

---

## 4. Phase 4 — Week 05 Acceptance Matrix (`C-W05-01..09`)

The table below maps all 9 acceptance test cases defined in `W04_C_application-requirements-freeze.md` to current implementation, existing automated test coverage, additional physical requirements, and hardware readiness status:

| Test ID | Test Scenario | Current Implementation | Existing Host Test Coverage | Required Physical Firmware / Device Behavior | Bench Evidence Expected | Current Status |
|---|---|---|---|---|---|---|
| **C-W05-01** | **Deterministic 100 Hz Sine / Counter Ingestion** | Push ingestion seam in `StreamManager.ingest_device_packet`, `packet_to_sample_block` | `test_known_48khz_mono_synthetic_signal_preservation` (`SOFTWARE_KNOWN_ANSWER`) | MCU transmits continuous 100 Hz synthetic sine or counter at 48 kHz over Native USB | Saved bench WAV + JSON session, FFT confirming 100 Hz peak on real USB capture | **NOT TESTED ON HARDWARE** (Host Preflight Ready) |
| **C-W05-02** | **Protocol / Profile Handshake** | `DeviceCapabilities.validate_compatibility()`, `DeviceRuntime.complete_handshake()` | `test_successful_48khz_mono_handshake`, `test_block_size_negotiation` | MCU announces capabilities on connection, negotiates block size (512), awaits start command | Device event log showing handshake validation, status JSON confirming 48 kHz mono | **NOT TESTED ON HARDWARE** (Host Preflight Ready) |
| **C-W05-03** | **Intentional Sequence Gap Telemetry** | `DeviceIntegrityStats.record_packet()`, `StreamQualityMonitor.inspect_block()` | `test_stream_ingest_duplicate_and_gap_telemetry_detection` | MCU test firmware injects intentional packet skip (e.g. sequence 0→2) | Telemetry counters show exact missing packet count (`sequence_gaps == 1`), `session.json` logs gap | **NOT TESTED ON HARDWARE** (Host Preflight Ready) |
| **C-W05-04** | **Fragmented & Multi-Frame USB Reads** | `DevicePacketDecoder` abstract interface in `device_runtime.py` | Unit framing concepts tested; byte stream defragmenter pending protocol freeze | MCU transmits back-to-back frames over USB endpoint without stalling | Host reconstructs frames across chunk boundaries (64B, 512B, 4096B reads) with 0 sample loss | **BLOCKED BY WIRE PROTOCOL FREEZE** (DW03-12 / DW03-10) |
| **C-W05-05** | **Exact Sample Count Preservation** | `SessionRecorder.record_block()`, float32 WAV serialization | `test_multi_block_sample_ordering_and_continuity_across_boundaries` | MCU transmits exactly $N$ samples (e.g. 48,000 samples = 1.0 s) and ceases | Recorded WAV has exactly $N$ samples; WAV readback equals ingested data | **NOT TESTED ON HARDWARE** (Host Preflight Ready) |
| **C-W05-06** | **Clean Start / Stop Lifecycle** | `StreamManager.start_recording()`, `stop_recording()`, `stop_streaming()` | `test_wav_json_integrity_and_sha256_verification`, `test_full_valid_handshake_and_streaming_lifecycle` | MCU starts DMA/USB on START command, pauses DMA/USB on STOP command | Clean state transitions without trailing orphan samples or USB buffer deadlocks | **NOT TESTED ON HARDWARE** (Host Preflight Ready) |
| **C-W05-07** | **Disconnect & Interruption Handling** | `DeviceRuntime.handle_disconnect()`, `StreamManager.handle_device_disconnect()` | `test_safe_recording_finalization_after_device_interruption`, `test_reconnect_lifecycle_after_interruption` | Host detects physical cable detachment, transitions to INTERRUPTED, cleanly re-enumerates on replug | `session.json` written with `termination_reason='device_disconnected'`; no hung process | **NOT TESTED ON HARDWARE** (Host Preflight Ready) |
| **C-W05-08** | **Corrupt CRC / Header Rejection** | CRC check in `ingest_device_packet`, compatibility validation | `test_packet_with_crc_failure_rejected_by_adapter`, `test_unsupported_acquisition_profile_rejection_at_handshake` | MCU firmware test mode injects bad CRC byte or malformed length | Corrupt packet dropped, `crc_failures` counter incremented, 0 audio artifacts | **NOT TESTED ON HARDWARE** (Host Preflight Ready) |
| **C-W05-09** | **Sustained Bench Run Profile** | `DeviceIntegrityStats` telemetry tracking, rolling buffer, memory stability | Multi-block synthetic ingestion tested up to thousands of samples; sustained run pending HW | MCU streams continuously for 5–10 minutes without DMA underruns or buffer slips | Throughput log confirming ~192 kB/s payload rate, 0 dropped frames, stable host memory | **NOT TESTED ON HARDWARE** (Bench Run Pending Hardware) |

---

## 5. Items Blocked by Module B Decisions

The following concrete items cannot be implemented on the host without joint Module B agreement:

1. **Wire Framing Parser Implementation:**
   - Blocked until **DW03-12** (CDC-ACM vs Vendor Bulk), frame header layout (16-byte illustrative concept), and sync magic (`0xAA55`) are formally approved. Once agreed, a concrete `CDCByteStreamDecoder` implementing `DevicePacketDecoder` will be written and tested. No production decoder is implemented against the unapproved layout.
2. **Bit Alignment Inside 32-Bit Container:**
   - Blocked until Module B confirms whether I2S DMA produces LSB-aligned sign-extended words (normalizing by $2^{23}$) or MSB-aligned left-justified words (normalizing by $2^{31}$).
3. **CRC Policy & Parameters (DW03-09):**
   - Blocked until **DW03-09** is closed. CRC-16-CCITT is proposed by Module C, but its polynomial, initialization, reflection, coverage, byte order, and error handling remain unfinalized.
4. **Hardware Acquisition Profile Reconciliation:**
   - The purchased microphone is the **INMP441 breakout module** (sourced due to PUI EB-R lead-time constraints). The host strictly preserves the existing PUI Rev-A profile (`rev_a_pui_dmm4026`) and 4 kHz development profile (`dev_4khz_legacy`). A separate INMP441 profile will be introduced only after Module B supplies verified I2S driver configuration and DMA alignment evidence.
5. **USB Vendor / Product ID (VID/PID):**
   - Host candidate discovery (`poll_candidates`) is truthful and pending until Espressif Native USB descriptors (or default VID:PID `0x303A:0x1001`) are declared by firmware.

---

## 6. Action Plan When Real ESP32-S3 Arrives

1. **Connect Native USB Port:**
   - Connect the ESP32-S3 DevKit's Native USB port (separate from UART/log port) using a verified data-capable USB cable.
2. **Verify Enumeration:**
   - Inspect Device Manager (Windows) or `ls /dev/ttyACM*` (Linux) to verify virtual COM port assignment.
3. **Bring Up CDC-ACM Transport Adapter:**
   - Instantiate host CDC transport adapter pointing to the discovered COM port.
4. **Execute Synthetic Acceptance Tests:**
   - Flash synthetic 100 Hz sine / counter firmware onto ESP32-S3.
   - Run acceptance tests `C-W05-01` through `C-W05-08` in order.
   - Log all telemetry, WAV recordings, and SHA-256 hashes to `experiments/sessions/`.
5. **Mark Gate G1:**
   - Review actual bench logs with Ozan and Kaan; mark Gate G1 passed only upon physical validation.
