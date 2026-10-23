# Morning integration audit

The baseline is [MORNING_BASELINE_AUDIT](MORNING_BASELINE_AUDIT.md); execution
results and remaining limitations are in [MORNING_RELEASE_REPORT](MORNING_RELEASE_REPORT.md).

## Eight-layer review

| Layer | Inspected implementation and conclusion |
| --- | --- |
| Transducer | Seller dossier and TDK source rechecked; delivered breakout/PCB/power/receipt unverified. Pins4/5/6 provisional, source0 off. Separate pin plan and inspection form added. No phantom/chestpiece purchased/accepted. |
| Embedded | g1/acquisition/app_main/usb_transport/i2s_source/Kconfig/CMake/lock inspected. Fixed bounded buffers, task ownership, atomic link callbacks, per-second health logs and UART-only debug. No new firmware wire change needed. Actual IDF build succeeds. |
| Transport | Canonical header/control sizes/opcodes/CRC, C serializer, Python codec/session and firmware inspected. Frozen vectors plus new signed edge, wrap and partial vectors compared byte-for-byte to actual C serializer. Malformed/truncated/CRC tests preserved. |
| Windows runtime | Production engine owns reads/writes. Open failure closes serial; worker exception guarantees teardown; rejected HELLO cannot READY; reconnect cannot replace an unclosed owner. Single deliberate COM selection, passive discovery and actionable cancellation. |
| DSP/recording | integer24 /2^23 → float32 exactly represents all24-bit input levels; raw WAV precedes processing and independently reopens. Recorder start/append/stop protected by RLock; existing sessions cannot be overwritten. STOP finalizes active recording. New START resets DSP/display; state retained between blocks within session. |
| AI research | No frozen artifacts, metrics or training files changed. Actual full suite with PyTorch passes. New environment has no torch; backend/USB remain available, inference is503. Positive inference fixtures require torch and are separately reported. No auto inference on live mic. |
| Desktop | Existing DeviceView/bridge endpoint/actions/types audited. Explicit simulation/failure/pass label tests added; no physical device inferred from simulator-only port list. Source0 target also triggers STOP. Bounded cross-thread display delivery runs on client event loop. |
| Release | Main only, passive board-absent checks, actual IDF/C/Python/frontend/Rust builds/tests, clean venv install and packaged backend HTTP smoke. Installer compilation and interactive verification are distinct evidence. |

## Canonical freeze

Authority: `docs/engineering/protocol/B_C_CANONICAL_PROTOCOL_V0_1.md`.
Header40 + CRC4, magic0xAF534331, major1, mono48kHz, meaningful24/container32,
LSB sign-extended S32LE, Profile2/encoding1, standard count256 →1068 bytes.
Opcodes AUDIO1, STATUS2, START3/4, STOP5/6, ERROR15, HELLO16/17.
Payload lengths HELLO4/24, START16/32, STOP8/72, STATUS72, ERROR8;
controls count0. CRC IEEE covers header+payload. No struct-to-wire cast.

G1 `(index*16807+7)&0xffffff`, signed conversion at0x800000. 480000 samples,
1875 packets,1920000 PCM bytes,2002500 AUDIO wire bytes. Sequence wraps32;
session is64-bit/nonzero/fresh. Requested-target exhaustion waits for STOP_REQ,
then drains FIFO/USB before STOP_ACK. No assumption that queued equals received.
Standard G1 disallows a short final frame; generic protocol/short target permits it.
Partial writes count retry/backpressure; not automatically loss. Physical timing
check9..15s is a coarse host test, not a48kHz clock calibration.

Current canonical docs and Module B package match this contract. Alternative
legacy CRC16 decoder remains a separate interface and is not the USB canonical
path. Historical G1/First Contact evidence stays dated; current entrypoint is the
Turkish quickstart. A historical manifest's machine paths are not laptop instructions.

## Failure injection matrix

All PASS entries below mean **software behavior**, never physical measurement.
Paths abbreviated: F=`firmware/tests/test_g1.py`, C=`tools/protocol_lab/python/`,
M=`software/tests/test_morning_release.py`, U=`software/tests/test_usb_integration_bridge.py`,
FC=`software/tests/test_first_contact.py`, D=`software/tests/test_device_runtime.py`.

| Requested condition | Software evidence / expected result | Physical status |
| --- | --- | --- |
| 1 no board | FC passive-preflight + actual doctor; NOT_DETECTED/no open | Board absent |
| 2 wrong port | U invalid-port;400, no ready | NOT_EXECUTED |
| 3 occupied port | D concurrent ownership/transport checks; access exception surfaced, no bypass | Windows competing application NOT_EXECUTED |
| 4 unplug | F disconnect + C negative16 + interrupted-recording tests | NOT_EXECUTED |
| 5 re-enumeration | M passive watch changes COM1→absent→COM2; never auto open/select | NOT_EXECUTED |
| 6 wrong firmware | M unsupported-firmware + FC selected-manifest version; ERROR/prevents START | NOT_EXECUTED |
| 7 nonce | F wrong-nonce + C nonce mismatch; reject | NOT_EXECUTED |
| 8 HELLO timeout | C negative handshake gates + desktop failed-connect; no READY | NOT_EXECUTED |
| 9 source unsupported | F invalid-state/mode/config; error2, G1 still available | NOT_EXECUTED |
| 10 rejected START | F invalid state/config; no streaming | NOT_EXECUTED |
| 11 wrong accepted fields | C START_ACK exact-field negative cases | NOT_EXECUTED |
| 12 length | C invalid count/length + FC count1025 | NOT_EXECUTED |
| 13 CRC | C/F corrupt packet tests; fail, no accepted corrupt audio | NOT_EXECUTED |
| 14 duplicate | C negative9 + FC counters; FAIL | NOT_EXECUTED |
| 15 missing | C negative8 + FC counters; FAIL | NOT_EXECUTED |
| 16 index | C index negative + FC observer; FAIL | NOT_EXECUTED |
| 17 wrong sample | C negative10 + FC mismatch; FAIL | NOT_EXECUTED |
| 18 partial write | F backpressure/partial + host short command-write check | NOT_EXECUTED |
| 19 overflow | F control/ring overload + FC falsified telemetry; visible failure | NOT_EXECUTED |
| 20 sample loss | F live counters + FC dropped; FAIL | NOT_EXECUTED |
| 21 STOP under stream | F partial/backpressure STOP + M repeated API session | NOT_EXECUTED |
| 22 target before STOP | F full480000 and partial target; STOP_ACK drains all | NOT_EXECUTED |
| 23 missing ACK | FC timeout evidence retained; no pass, port released on disconnect | NOT_EXECUTED |
| 24 telemetry mismatch | FC parameterized final counters; FAIL | NOT_EXECUTED |
| 25 storage error | FC ingestion error + recording tests + M raw-before-DSP; retain failed/incomplete evidence | Actual full disk NOT_EXECUTED |
| 26 invalid WAV | M qualify corruption and recording integrity tests | No real sensor file |
| 27 I2S init failure | F live acquisition failure/error6; boot profile failure code reviewed and enabled build compiled | Actual IDF init failure NOT_EXECUTED |
| 28 absent microphone | Default-disabled firmware and no-sensor startup reviewed/compiled | Electrical absence behavior NOT_EXECUTED |
| 29 zero input | M zero/constant/saturation screen; no microphone PASS | NOT_EXECUTED |
| 30 repeated sessions | F restart + FC engine reconnect + M API recording sessions | NOT_EXECUTED |
| 31 application restart | Desktop subprocess lifecycle + M shutdown closes owner | Interactive app restart NOT_EXECUTED |
| 32 inference unavailable | M missing dependency returns503 while USB HELLO succeeds; clean no-torch environment | No hardware inference requested |
| 33 missing dependency | M `python -S` actual subprocess preflight; MISSING/actions | No installation changes |
| 34 invalid COM argument | M argparse missing port + U wrong port; no guessing | NOT_EXECUTED |
| 35 cancellation | FC flash denied and M UART capture denied; no writes/opens after denial | No physical write attempted |

## Scientific and diagnostic boundaries

Existing scientific/filter/segmentation, invalid/silent-signal, display, recording,
fault catalog/Flight Recorder and ML tests are included in the full regression.
Nominal acquisition rate, sample-count duration, host arrival estimates, display
decimation and DSP/WAV rates remain distinct. Welch uses actual session fs;
PSD density is FS²/Hz (10log10 for power dB), filter cutoffs/provenance stay separate
from raw data. No changed clinical interpretation, threshold or training metric.
Performance test still uses phase-continuous100Hz across packets, >2x real-time
threshold unchanged; new wire-boundary test includes signed full-scale extrema.

Diagnostic provenance uses existing stable enum names: OBSERVED_HOST;
REPORTED_BY_FIRMWARE (requested FIRMWARE_REPORTED); DERIVED_FROM_SAMPLES
(DERIVED); INJECTED_SIMULATION (SOFTWARE_SIMULATED); NOT_MEASURED.
Live timestamp estimates are documented as estimates, not new enum aliases.
Session diagnostic origin is explicit; simulator events cannot impersonate physical
firmware reports. Journal memory500, write queue1000, five rotated5MB backups;
dedup and secret redaction remain. Local paths/USB identifiers can remain in
private bundles: inspect/redact before sharing, never publish raw recordings.

| Fault | Student action |
| --- | --- |
| HELLO timeout | Check selected native CDC, close owning monitor, confirm firmware and UART/binary separation |
| CRC | Preserve frame/failure bundle; check protocol/source version, parser, cable and power |
| Zero/constant mic | Check measured3.3V/GND, WS/BCLK/SD, L/R and alignment; silence alone proves nothing |
| USB stalled | Preserve queue/timeout evidence; check owner reader, bounded backpressure, cable and task health |
| Disk/recording error | Stop, preserve incomplete marker/WAV, inspect free space/permissions; do not overwrite original |

Known recorder limit: short accepted audio is RAM-buffered until STOP. Process
crash can leave only an incomplete marker; durable streaming disk writes are a
future improvement, not claimed by this RC. No real USB, PSRAM, acoustic or stack
measurement was substituted with software results.
