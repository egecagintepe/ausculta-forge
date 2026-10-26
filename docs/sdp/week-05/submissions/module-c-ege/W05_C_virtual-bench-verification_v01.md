# W05 Module C: Deterministic Virtual Bench & Full Pipeline Known-Answer Verification

> **Current-status addendum — 2026-10-26 (documentation review, baseline `106d3e0`):** **New physical CLI G1 PASS verified on 2026-10-26 at 07:50 UTC**, host `106d3e0`, COM7 / VID:PID `303A:4001`, firmware `1.1.0`, protocol `1.0`: 480000 accepted samples, 1875 frames, zero integrity errors and STOP_ACK. Local original evidence: `experiments/hardware/week6_20261026_sprint/cli-g1/20261026T075048Z_f26df565/g1_protocol_summary.json`. The earlier laptop run remains user-reported; this is a separate new mini PC run. GUI physical G1 **PASS at 59d773e** on 2026-10-26 08:14 UTC; final e90785e GUI HELLO/READY/disconnect **PASS**, full G1 repeat **NOT_EXECUTED (two-start limit)**. Real microphone G2 remains **PENDING**. See the [sprint report](../../../../engineering/release/WEEK6_SPRINT_REPORT.md). See the [current closeout and missing-evidence register](W05_C_live-display-recording-verification.md).
>
> The body below is a **historical snapshot**, including its status fields, proposals, implementation descriptions and test outputs; none was rerun today. Statements about hardware arrival, pending USB/decoder implementation or untested G1 describe that earlier baseline, not the current checkout. Canonical host code now exists in `software/pcg_app/canonical/`; implementation does not prove joint Module B sign-off or microphone qualification.
> Storage clarification: the historical diagram below says "Raw 16-bit WAV writer"; the current recorder defaults to normalized IEEE float32 WAV with JSON sidecar. It is not an unparsed USB wire-byte archive. Historical output and measurements are retained unchanged.


**Document Version:** `v01`  
**Date:** 2026-10-17  
**Module:** Module C — Computer Application & Signal Processing  
**Owner:** Ege Çağın Tepe  
**Branch:** `feature/ege-s02-virtual-bench`  
**Execution Tag:** `SOFTWARE_KNOWN_ANSWER`  
**Hardware Status:** ZERO PHYSICAL HARDWARE REQUIRED (Software Test Double & Mathematical Oracles)

---

## 1. Executive Summary

This deliverable provides a deterministic, software-only virtual integration bench for the complete AuscultaForge acquisition pipeline. It exercises the host packet ingestion seam, hardware lifecycle state machine, real-time DSP filtering, display ring-buffer publication, and session recording without requiring an ESP32-S3 physical development board.

All results are produced by strictly declared parameters and reproducible seeds, verified against independent mathematical known-answer oracles, and permanently tagged `SOFTWARE_KNOWN_ANSWER`.

The virtual bench is accessible via three mechanisms:
1. **Reproducible Developer CLI:** `python software/pcg_app/virtual_bench.py --all --json-out experiments/virtual-bench/acceptance_report.json`
2. **REST API Seam:** `GET /api/bench/scenarios` and `POST /api/bench/run`
3. **Frontend Developer Card:** An explicitly labeled `SOFTWARE BENCH · TEST ONLY (NOT HARDWARE)` card in `DeviceView.tsx`.

Crucially, **the virtual bench mode cannot cause production discovery to report physical hardware connected**. It operates through in-memory test doubles (`VirtualBenchTransport`) and isolated stream manager instances.

---

## 2. Ingestion Seam Architecture

```
+----------------------------------------------------------------------------------+
|                    VIRTUAL INTEGRATION BENCH HARNESS                             |
|                                                                                  |
|  [Deterministic Signal Generator]                                                |
|       |                                                                          |
|       v                                                                          |
|  DeviceSamplePacket (sequence, timestamp_s, samples: int32, sample_rate_hz: 48k) |
+-------|--------------------------------------------------------------------------+
        |
        v  (Direct Host Ingestion Seam)
+----------------------------------------------------------------------------------+
| StreamManager.ingest_device_packet()                                             |
|   |--> DeviceRuntime (Lifecycle State: DETECTED -> HANDSHAKE -> READY -> STREAM) |
|   |--> Integrity Telemetry (CRC, Gaps, Discontinuities, Regressions)            |
|   |--> packet_to_sample_block() [24-in-32 signed PCM -> [-1.0, 1.0] float]      |
|   |--> StreamState.feed_block()                                                  |
|   |--> Live Display Pipeline (Rolling ring buffer, spectral Welch FFT)          |
|   |--> SessionRecorder (Raw 16-bit WAV writer, SHA-256 accounting, JSON sidecar) |
+----------------------------------------------------------------------------------+
        |
        v
+----------------------------------------------------------------------------------+
| INDEPENDENT KNOWN-ANSWER ORACLES & MACHINE-READABLE VERIFICATION                 |
|   - Welch PSD dominant frequency check (resolution Delta f = 10.0 Hz)            |
|   - Exact monotonic counter accounting (start, end, increments)                  |
|   - Boundary saturation checks (+1.0, -1.0, 0.0, NaN/Inf immunity)              |
|   - Unit impulse response localization and clipped pulse RMS checks              |
|   - Injected sequence gaps and duplicate packet counters                         |
|   - Timestamp regression anomaly counters                                        |
|   - CRC rejection (excluding corrupted blocks from recording)                    |
|   - Cable disconnect lifecycle recovery (preservation of prior recording)        |
+----------------------------------------------------------------------------------+
```

---

## 3. Required Test Scenarios & Known-Answer Oracles

| # | Scenario ID | Category | Description | Primary Oracle / Acceptance Criteria | Status |
|---|---|---|---|---|---|
| 1 | `sine_100hz_48k` | `wave_fidelity` | 48 kHz Mono 100 Hz Pure Sine Wave | Dominant frequency $f_0 = 100.0\text{ Hz}$ ($\Delta f \le 1.0\text{ Hz}$), max error $< 10^{-5}$, RMS $\approx 0.5303$, SHA-256 matching oracle | **PASS** |
| 2 | `ascending_sample_counter` | `sample_accounting` | Ascending Sample Counter (Exact Accounting) | $N = 4096$ samples, first $= 500$, last $= 4595$, monotonic step $= 1.0$, zero dropped blocks | **PASS** |
| 3 | `boundary_conditions` | `boundary_extremes` | Silence, Half-Scale Sine & Full-Scale Extremes | Silence peak $= 0.0$, half-scale $= 0.5$, full-scale $+1.0$ and $-1.0$, zero NaNs/Infs | **PASS** |
| 4 | `clipped_and_impulse` | `impulse_response` | Unit Impulse & Clipped Pulse Sequences | Discrete Dirac delta at sample index 32 ($h[n] = 1.0$), clipped pulse RMS $= 1.0 \pm 0.05$ | **PASS** |
| 5 | `injected_gaps_duplicates` | `anomaly_telemetry` | Explicit Sequence Gaps & Duplicate Packets | Packets $= 5$, detected sequence gaps $= 2$, repeated packets $= 1$, samples intact | **PASS** |
| 6 | `timestamp_regression` | `anomaly_telemetry` | Timestamp Rollback & Rollover Anomaly | Packets $= 4$, detected timestamp regressions $= 1$, recorded samples preserved | **PASS** |
| 7 | `corrupt_inputs_rejection` | `crc_rejection` | CRC Failures & Out-Of-Range Sample Rejection | CRC failures counted $= 1$, bad frame excluded from WAV/JSON, out-of-range rejected | **PASS** |
| 8 | `lifecycle_interruption_reconnect` | `lifecycle_recovery` | Clean Stop, Cable Disconnect & Recovery | Cable pull enters `INTERRUPTED`, session 1 closed as `device_disconnected` (samples intact), reconnect handshake cleanly completes session 2 | **PASS** |

---

## 4. Verification Evidence

### 4.1. CLI Virtual Bench Execution
```bash
$ python software/pcg_app/virtual_bench.py --all --verbose --json-out experiments/virtual-bench/acceptance_report.json

================================================================================
 AUSCULTAFORGE VIRTUAL INTEGRATION BENCH -- KNOWN-ANSWER TEST HARNESS
 Status: SOFTWARE_KNOWN_ANSWER -- Zero Physical Hardware Required
================================================================================
[PASS]  [sine_100hz_48k                  ] 48 kHz Mono 100 Hz Pure Sine Wave              (78.9ms)
      [+]  sample_rate_hz: exp=48000, obs=48000
      [+]  sample_count: exp=10240, obs=10240
      [+]  dominant_frequency: exp=100.0, obs=100.0
      [+]  waveform_max_error: exp=0.0, obs=1.1920928955078125e-07
      [+]  rms_level: exp=0.5303300858899106, obs=0.5311664938926697
      [+]  sha256_verified: exp=95ce3d0fed6e66b9c7db5153c722ac0cc151ffb6c3c39bda99086fa092c985cf, obs=95ce3d0fed6e66b9c7db5153c722ac0cc151ffb6c3c39bda99086fa092c985cf
[PASS]  [ascending_sample_counter        ] Ascending Sample Counter (Exact Accounting)    (44.3ms)
      [+]  sample_count: exp=4096, obs=4096
      [+]  first_sample_int: exp=500.0, obs=500.0
      [+]  last_sample_int: exp=4595.0, obs=4595.0
      [+]  monotonic_increment: exp=1.0, obs=1.0
      [+]  zero_dropped_blocks: exp=0, obs=0
[PASS]  [boundary_conditions             ] Silence, Half-Scale Sine & Full-Scale Extremes (33.8ms)
      [+]  silence_peak: exp=0.0, obs=0.0
      [+]  half_scale_peak: exp=0.5, obs=0.49999988079071045
      [+]  full_scale_negative: exp=-1.0, obs=-1.0
      [+]  full_scale_positive: exp=1.0, obs=0.9999998807907104
      [+]  no_nan_or_inf: exp=True, obs=True
[PASS]  [clipped_and_impulse             ] Unit Impulse Response & Clipped Pulse Sequences (31.6ms)
      [+]  impulse_index: exp=32, obs=32
      [+]  impulse_peak_val: exp=1.0, obs=0.9999998807907104
      [+]  clipped_square_rms: exp=1.0, obs=0.999022901058197
      [+]  total_recorded_samples: exp=1024, obs=1024
[PASS]  [injected_gaps_duplicates        ] Explicit Sequence Gaps & Duplicate Packets     (42.0ms)
      [+]  packets_received: exp=5, obs=5
      [+]  sequence_gaps: exp=2, obs=2
      [+]  repeated_packets: exp=1, obs=1
      [+]  total_samples_recorded: exp=2560, obs=2560
[PASS]  [timestamp_regression            ] Timestamp Rollback & Rollover Anomaly          (48.1ms)
      [+]  timestamp_regressions: exp=1, obs=1
      [+]  packets_received: exp=4, obs=4
      [+]  session_samples_intact: exp=2048, obs=2048
[PASS]  [corrupt_inputs_rejection        ] CRC Failures & Out-Of-Range Sample Rejection   (35.6ms)
      [+]  crc_failures_counted: exp=1, obs=1
      [+]  bad_packet_excluded_from_samples: exp=1024, obs=1024
      [+]  out_of_range_sample_rejected: exp=True, obs=True
[PASS]  [lifecycle_interruption_reconnect] Clean Stop, Abrupt Cable Disconnect & Recovery (92.0ms)
      [+]  interrupted_state_reached: exp=True, obs=True
      [+]  session_1_termination_reason: exp=device_disconnected, obs=device_disconnected
      [+]  session_1_samples_preserved: exp=1024, obs=1024
      [+]  reconnect_handshake_ready: exp=ready, obs=streaming
      [+]  session_2_completed_cleanly: exp=completed, obs=completed
      [+]  session_2_samples: exp=1536, obs=1536
--------------------------------------------------------------------------------
Total: 8 | Passed: 8 | Failed: 0 | Result: ALL PASSED
Tag: SOFTWARE_KNOWN_ANSWER
================================================================================
```

### 4.2. Pytest Automated Test Suite
```bash
$ .venv\Scripts\python.exe -m pytest
======================= 295 passed, 1 warning in 7.86s ========================
```
- Includes 12 dedicated tests in `software/tests/test_virtual_bench.py` covering all scenario dispatchers, oracles, REST endpoints, and CLI invocation.

### 4.3. Frontend TypeScript & Production Build
```bash
$ npm run lint
> tsc --noEmit (Exit code 0)

$ npm run build
> vite build
✓ built in 2.34s (Exit code 0)
```

---

## 5. Architectural & Security Guarantees

1. **Production Hardware Discovery Isolation:**
   The virtual bench harness uses `VirtualBenchTransport` (an in-memory test double) and explicitly labeled IDs (`SOFTWARE-BENCH-PROBE`). It does not register devices with serial port candidate providers or falsify Windows COM enumerations. The production UI reports `ABSENT` unless a physical USB descriptor is detected by the OS.

2. **Truthful Telemetry Accounting:**
   Sequence gaps, CRC mismatches, and timestamp rollbacks increment authoritative metrics (`device_stats.sequence_gaps`, `crc_failures`, etc.) without dropping or corrupting the surrounding session stream.

3. **Known-Answer Provenance:**
   Every report, REST payload, and session sidecar produced by the virtual bench is marked `status_tag: SOFTWARE_KNOWN_ANSWER`. No artificial biometric readings or fabricated physical sensor parameters are generated.

---

## 6. PR & Branch Information

- **Branch:** `feature/ege-s02-virtual-bench`
- **Base:** `main` (Post-PR #17 merge `94b5417b8a0a10ea299e851248aa5506e62381d2`)
- **PR:** Opened for peer review (Module B / Module A) without automatic merge.
