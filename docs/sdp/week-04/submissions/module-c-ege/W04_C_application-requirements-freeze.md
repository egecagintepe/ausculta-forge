# W04 Module C — Computer Application Requirements Freeze

**Course:** EEE495 — Senior Design Project I  
**Week:** 04 (starting 12 October 2026)  
**Owner:** Ege Çağın Tepe — Module C, Computer Application & Quality Assessment  
**Status:** REQUIREMENTS DRAFT COMPLETE / READY FOR TEAM REVIEW. Functional Module-C requirements are specified below; physical B→C protocol fields and shared engineering decisions remain OPEN until Ozan/Ege review.  
**Scope:** Student PCG research prototype; acoustic phantom and public CirCor data only. No human recordings or diagnostic claims.

## 1. Objective and freeze boundary

Define testable host-application requirements for **live display, signal-processing views, recording, provenance metadata and recording-quality feedback**, as requested by the advisor's Week-04 schedule. Prepare a verifiable acceptance contract for Week-05's known/synthetic MCU→PC stream.

**Module C can define what must be accepted and verified without selecting another module's hardware.** This document does not assert that the PCM1808 ADC, USB CDC-ACM, Vendor Bulk, application CRC, binary header offsets or the final signed-PCM wire representation have been selected. These are shared or Module-B decisions.

### Evidence used

- [Week-02 Module-C implementation audit](../../../week-02/module-c-status.md).
- [Week-02 B→C host interface requirements](../../../week-02/bc-interface-requirements.md).
- [Week-02 mandatory physical measurement and quality plan](../../../week-02/measurement-quality-plan.md).
- [Week-03 known-condition quality verification](../../../week-03/submissions/module-c-ege/W03_C_quality-metrics-validation.md).
- [Week-03 shared decisions](../../../week-03/decisions.md), in particular DW03-08/09/10/12/13.
- Advisor's weekly plan and assessment criteria: measurable requirements, independent known-input verification and script-generated results.

## 2. Testable Module-C requirements

A requirement ID identifies a future **test/inspection obligation**, not a claim that Week-04 hardware testing has already passed.

| ID | Requirement / interface condition | Acceptance evidence | Target / ownership |
|---|---|---|---|
| C-W04-FR01 | **Live waveform:** Render incoming accepted PCG samples as a continuously updated time-domain view with sample-rate/time and amplitude context. Keep display data bounded/decimated and separate from the full-rate recording path. | Feed a known multi-block stream; compare visible time scale and peaks against the input, and verify that display decimation does not change stored sample count. A rolling window of at least 5 s is a proposed UI acceptance target, not a verified physical result. | Module C; software verification, then Week-05 B→C |
| C-W04-FR02 | **Spectral view:** Display FFT/spectrum and/or spectrogram that supports inspection of the mandatory **20–500 Hz** PCG characterization band. Show sampling frequency and meaningful frequency axes. | Known 100 Hz sine produces the corresponding dominant frequency in an automated spectral test and a visible spectral representation. This is a software oracle, not a phantom transfer-response result. | Module C; software verification |
| C-W04-FR03 | **Raw accepted-stream recording:** Record the full-rate `SampleBlock` stream to an unfiltered WAV; do not replace source data with a filtered, normalized-for-display, or decimated visualization. Preserve the accepted float32 sample values exactly through WAV readback. | Known sample arrays: number/order of written samples match ingested samples, float32 WAV readback matches accepted `SampleBlock` values. Original device integer payload bit-for-bit preservation is **not claimed** unless a separate raw-container mechanism is built/tested. | Module C; Week-03 software evidence exists; Week-05 real-stream test pending |
| C-W04-FR04 | **Provenance and session metadata:** A WAV session must have a machine-readable JSON sidecar containing source/session identity, rate, sample count, sequence/timestamp boundaries, recording/termination status, stream-quality report and a file hash. Include device/firmware/protocol/acquisition profile fields when Module B supplies verified data. | Record a known stream, reopen WAV + JSON and verify all required available fields, actual sample count and SHA-256. Missing physical device metadata must be marked unavailable, not invented. | Module C; Week-03 known-condition evidence, hardware provenance pending |
| C-W04-FR05 | **Processing separation:** Host filtering, spectrum and quality calculations must use the declared physical sample-rate profile; original accepted samples remain available separately from processed data. | Controlled signal test confirms analysis values while stored accepted sample arrays remain unchanged. Reject a sample-rate change during one recording instead of silently mixing rates. | Module C |
| C-W04-FR06 | **Deterministic recording-quality checks:** Calculate digital RMS/peak and full-scale saturation, continuity gaps, sample-rate inconsistency and any valid device error counters. Present measured/observed flags separately from uncalibrated acoustic quality claims. | Known sine amplitude 0.5 gives RMS ≈ 0.353553; 8 full-scale hits / 1000 samples yields fraction 0.008; sequence 0→3 yields two missing blocks. These are deterministic **software** test cases. | Module C; covered by Week-03 evidence |
| C-W04-FR07 | **Source/playback parity:** Support open CirCor PCG playback and deterministic synthetic sources through the same core `SampleBlock` DSP/recording path. Keep public dataset identity and processing parameters in experimental provenance. | Load a known WAV, process and record through the same core path and confirm reproducible sample accounting. Physical speaker/phantom playback still belongs to a later combined A/B/C test. | Module C |
| C-W04-IF01 | **Device and profile validation:** Before accepting physical frames, verify declared protocol version/type, supported sample rate, channel count, sample encoding/container/alignment, firmware/device identity and stream lifecycle. Reject unsupported combinations rather than silently reinterpreting samples. | Supported synthetic handshake accepted; incompatible version, rate, channel count or sample packing rejected with an explicit error state. Exact wire format remains a joint B/C decision. | Joint B→C interface; Week-05 |
| C-W04-IF02 | **Continuity and fault visibility:** Every accepted frame must be traceable through a monotonic sample/block continuity mechanism and a declared sample count. Host must expose gaps, duplicates/out-of-order frames, hardware buffer overflow where reported, and disconnect/reconnect conditions. USB read boundaries are not assumed to equal application frames. | Inject an intentional sequence/sample-index gap and verify the exact missing count; split/concatenate framed byte reads; verify malformed messages fail safely and session metadata records errors. | Joint B→C interface; Week-05 |
| C-W04-IF03 | **Integrity policy:** If a frame CRC/checksum is chosen, verify it and reject corrupt frames; if not, justify USB link integrity plus framing, continuity and status checks. Never display an unimplemented CRC indicator as a real hardware measurement. | Joint signed-off B/C policy, parser tests corresponding to that policy, and explicit metadata/telemetry semantics. | **OPEN** — DW03-09 |
| C-W04-IF04 | **Recording control and status:** Physical device `START`/`STOP`/status semantics must be deterministic; UI can distinguish absent, ready, streaming, interrupted, incompatible and error states. Offline/mock modes may never masquerade as connected hardware. | Controlled state-transition and disconnect/reconnect tests; device status reflects verified backend events. | Module C with Module B firmware |
| C-W04-VAL01 | **Independent validation and reproducibility:** Numeric tables/results must come from a script with retained input, environment/revision and raw evidence. Phantom capture/known-source similarity and six required physical measurements are not replaced by offline algorithm tests. | Clean-copy test execution produces consistent scripted outputs, with raw WAV/JSON and relevant Git/hardware versions; phantom data marked NOT YET MEASURED until collected. | Module C; A/B collaboration in Weeks 7–13 |

### Proposed host targets pending review

- **Physical medium already selected in DW03-08:** wired ESP32-S3 Native USB.
- **Nominal acquisition profile:** mono 48,000 Hz; not yet a finalized ECM/MEMS-independent wire layout. This remains subject to B/C agreement.
- **Illustrative MEMS container:** signed 24 meaningful bits in 32-bit slots; this is a reference proposal from Week 02, not universal input interpretation.
- **Working payload calculation for that proposal:** 48,000 × 4 = 192,000 payload bytes/s before packet overhead. Throughput acceptance is experimental, not inferred from the link's advertised rate.
- The host's legacy 4 kHz development/mock sources do **not** define the physical MCU acquisition profile.
- A five-second UI history window is a proposed visible-display target and must be verified at review. No arbitrary hardware SNR, latency, acoustic -3 dB tolerance or contact-loss threshold is invented here.

## 3. Current implementation and limits

The repository contains a Python `pcg_core` processing/recording implementation, the `pcg_app` FastAPI/WebSocket bridge and a React/TypeScript frontend. Relevant implementation paths include:

- `software/pcg_app/device_runtime.py`: semantic acquisition profile, compatibility checks and device-state foundation.
- `software/pcg_app/display_pipeline.py`: bounded display decimation and spectral frame support.
- `software/pcg_core/recording.py`: accepted sample-block float32 WAV, JSON session provenance and SHA-256.
- `software/pcg_core/streaming.py`: stream continuity monitoring.
- `software/pcg_core/scientific/signal_quality.py`: deterministic digital signal-quality calculations.
- `software/tests/test_recording.py`, `test_streaming.py`, `test_scientific_signal_quality.py`: known-condition test cases.

**Evidence status:** The Week-03 report documents analytical/software verification for RMS, clipping, continuity and recording. No tests were re-run merely by writing this Week-04 document. Real ESP32 USB handshake/frame parsing, physical stethoscope quality, phantom SNR, 20–500 Hz transfer function and hardware latency/drop rate remain **NOT YET VERIFIED / NOT YET MEASURED**.

## 4. Week-05 B→C integration acceptance matrix

Module B must provide its **own real MCU firmware** producing a declared known sample pattern over the selected physical transport. A host-only mock is useful for development but **does not independently pass the Week-05 MCU→PC integration gate**.

| Test ID | Given stimulus / setup | Required observation and retained evidence |
|---|---|---|
| C-W05-01 | MCU streams a deterministic 100 Hz sine or declared repeating counter pattern | Host receives the correct ordered waveform, with declared sampling rate and sample format; record the actual firmware SHA/profile |
| C-W05-02 | Protocol/profile handshake | Supported profile enters READY/STREAMING; unsupported profile rejected with clear reason |
| C-W05-03 | Deliberately skipped frame(s) or sample-index range | Exact continuity gap detected and logged; cannot infer physical loss from host arrival timestamps |
| C-W05-04 | Two frames in one USB read; one frame split across reads | Parser reconstructs declared frames; no silent missing/duplicate samples |
| C-W05-05 | Fixed known number of transmitted samples | Host ingested count equals recorded WAV sample count; playback yields equal accepted float32 samples |
| C-W05-06 | Clean start/stop | Correct status transitions and WAV + session JSON + hash output |
| C-W05-07 | Disconnect/reconnect during acquisition | No hung session or falsely healthy device state; interruption recorded truthfully |
| C-W05-08 | Malformed length/version/type and, if adopted, bad CRC | Unsupported/corrupted inputs rejected deterministically without crashes or fabricated telemetry |
| C-W05-09 | Agreed stream profile for a sustained bench run | Record throughput, buffer overruns and actual observed continuity; the 30-minute formal long-run characterization is separately scheduled for Week 08 |

**Reporting:** Each execution records command, device/firmware identity, Git SHA, capture duration, expected vs observed sample counts, log path and PASS/FAIL/PENDING. No predetermined PASS marks.

## 5. Dependencies and open decisions

| Reference | State as of Week-04 draft | Needed from |
|---|---|---|
| DW03-09 — application CRC policy | **OPEN**; requires explicit B/C review | Ege + Ozan |
| DW03-10 — sample representation/packing and frame count | **OPEN**; select signedness, byte order, payload representation and declared profile | Ege + Ozan |
| DW03-12 — CDC-ACM vs Vendor Bulk, parser/framing | **OPEN**; keep Native USB physical medium fixed | Ozan + Ege |
| DW03-13 — ECM ADC path | **OPEN**; do not tie host to an unapproved ADC | Ozan / Kaan / advisor |
| DW03-11 — Group-A purchase readiness | **OPEN** until actual candidate review/stock/order evidence | Kaan + Ozan + team |
| Hardware status/reconnect signaling | NOT YET TESTED on physical board | Ozan firmware + Ege host |

**Module-C position for joint review:** Prefer the least complex USB class that supports continuous declared throughput and a deterministic parser, reconnection and failure handling. Packet continuity is mandatory irrespective of application CRC. Keep the host acquisition profile sensor-agnostic and refuse ambiguous, undeclared sample formats.

## 6. Week-04 deliverables and sign-off

- [x] Measurable Module-C application and quality-feedback requirements recorded (this document).
- [x] Software known-answer oracle and repo evidence linked (from Week 03; not re-run now).
- [x] Week-05 B→C acceptance cases specified, with explicit physical-versus-mock distinction.
- [ ] Ozan/Ege jointly agree USB class, sample format/packing, counter semantics, parser framing and CRC policy; reflect conclusions in `docs/sdp/week-04/decisions.md` and the shared protocol documentation.
- [ ] Team/advisor review confirms any open hardware-dependent parameters without inventing measurements.
- [ ] Physical MCU→host verification is executed in Week 05, not claimed here.

**Review rule:** Freeze Module-C functional obligations now; do not mark the combined physical interface as final until the joint B/C contract is reviewed and tested. Update this file in a versioned follow-up if the agreed transport profile requires changes.

## 7. Next-week handoff

1. Obtain Ozan's actual firmware/transport and exact B→C profile, using an explicit versioned interface contract.
2. Attach the physical ESP32-S3 to the Python host ingest adapter; use known synthetic device samples before attaching microphone hardware.
3. Run C-W05-01 through C-W05-08 and retain reproducible logs/WAV/JSON; do not confuse current software tests with measured USB performance.
4. Coordinate Week-05 host acceptance with Module A's breadboard electrical noise-floor work and Module B's synthetic MCU stream.
