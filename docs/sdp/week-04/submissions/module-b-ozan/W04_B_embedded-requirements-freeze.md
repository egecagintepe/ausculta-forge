# W04 Module B — Embedded Requirements Freeze

**Week:** 4  
**Owner:** Ozan — Module B, Embedded Acquisition & Data Path  
**Status:** DOCUMENTED FOR REVIEW — NOT A FULL HARDWARE / B→C FREEZE  
**Last updated:** 2026-10-18

## 1. Objective and boundary

Define measurable requirements for the purchased ESP32-S3 N16R8 board, INMP441 I²S path, buffering/continuity/time metadata and wired device-to-host streaming. Separate source-backed facts, Week-5 implementation proposals, and facts requiring inspection or measurement on the physical board.

Week-5 G1 is a known synthetic stream from the physical ESP32-S3 to Ege's Python host over the jointly selected USB interface. G1 does not depend on the microphone or ECM ADC path. No firmware build, physical USB transfer, acquisition measurement or G1 pass is claimed by this Week-4 document.

## 2. Hardware identity and interface constraints

### 2.1 Purchased board identity

| Field | Current record | Status |
|---|---|---|
| Seller / listing | Direnc.net “ESP32 S3 N16R8 WiFi Bluetooth Board” | Purchased per owner-supplied order summary |
| Seller product code | DSTK22852 | Seller listing |
| Module designation in listing | ESP32-S3-WROOM-1-N16R8 | Seller-listed identity; physical marking not yet checked |
| Purchased quantity | 2 boards | Owner-reported order |
| Memory class | 16 MB flash + 8 MB octal PSRAM | Consistent with N16R8 listing |
| Exact PCB revision / board schematic | Not present in supplied purchase record | OPEN — inspect delivered board and obtain matching schematic |
| USB connector-to-controller routing | Not confirmed | OPEN — do not assume a USB-C connector is wired to USB-OTG |

The previous ESP32-S3-DevKitC-1-N8R8 candidate is superseded for the purchased prototype. Do not describe the purchased board as a DevKitC-1. Record real board markings/revision in the Week-5 bench log. Do not publish unique serial numbers, Wi-Fi MAC addresses or other personal/unique identifiers.

### 2.2 Pin and USB baseline

| Function | Proposed signal / SoC pin | Requirement and status |
|---|---|---|
| INMP441 bit clock | GPIO4 — BCLK/SCK | Proposed only; confirm exposed and unused on actual board |
| INMP441 word select | GPIO5 — WS/LRCLK | Proposed only; confirm header mapping |
| INMP441 serial data into MCU | GPIO6 — I²S DIN / SD | Microphone drives SD; MCU receives it |
| SoC USB D− / D+ | GPIO19 / GPIO20 | Espressif chip-level mapping; physical connector routing OPEN |
| INMP441 L/R | GND for left channel | Only after real module pin labels are checked |
| INMP441 supply | 3.3 V nominal test supply with local 100 nF decoupling | Datasheet operating conditions 1.8–3.3 V; characterized electrical limits 1.62–3.63 V. Do not use 3.63 V as the design target |
| Octal PSRAM pins | GPIO35, GPIO36, GPIO37 reserved | Do not assign to I²S/general I/O on N16R8 / octal-PSRAM module |

GPIO4/5/6 are a Week-5 starting proposal, not a frozen board pinout. Confirm actual silkscreen/header mapping and connector routing before wiring. ESP32-S3 USB Serial/JTAG is fixed-function; USB-OTG/TinyUSB is a separate firmware-capable device path. Ege and Module B must agree which enumerated interface the host uses.

Sources: [Direnc.net N16R8 board listing](https://www.direnc.net/esp32-s3-n16r8-wifi-bluetooth-board), [Espressif ESP32-S3-WROOM-1 / WROOM-1U datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf), [Espressif DevKitC-1 USB / PSRAM notes](https://documentation.espressif.com/api/resource/path/docs/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide.html). DevKitC-1 notes are used for chip-level mapping/PSRAM warnings only, not as proof that the purchased generic board is a DevKitC-1.

## 3. Measurable embedded requirements

| ID | Requirement | Acceptance / evidence | Status |
|---|---|---|---|
| MB-ACQ-01 | Nominal acquisition profile is 48,000 logical mono samples/s. | Firmware declares 48,000 Hz and 1 channel. During hardware test record actual WS/sample-clock frequency; initial bring-up acceptance within ±1% of 48 kHz with measured value logged. | Baseline documented; physical measurement OPEN |
| MB-ACQ-02 | INMP441 uses standard I²S: 24-bit two's complement, MSB-first, with the I²S one-SCK delay; 64 SCK cycles per WS frame. | Record slot width and peripheral mode; verify captured-word alignment and signedness. At 48 kHz, nominal BCLK is 3.072 MHz. | Datasheet-backed; physical capture OPEN |
| MB-ACQ-03 | Convert the selected INMP441 channel into one logical sample per WS period. | Host receives one sample per logical sample index; selected L/R slot documented. Do not treat the unused stereo slot as a second mono sample. | Requirement documented; implementation OPEN |
| MB-ACQ-04 | I²S acquisition is peripheral/DMA driven. Blocking USB writes must not run in an I²S ISR callback. | Source review checks bounded callbacks and a task/queue for USB output; log DMA timeout/overflow counters. | Architecture specified; firmware not implemented |
| MB-ACQ-05 | Initial DMA proposal: 256 WS frames/block and 4 descriptors/buffers. | One block spans 5.333 ms; four blocks span 21.333 ms. Raw buffer is 2,048 bytes/block if two 32-bit slots are stored, or 1,024 bytes/block for a true one-slot allocation. Log actual slot count, allocation and compile configuration. | Tunable proposal; validate on board |
| MB-ACQ-06 | DMA/ring-buffer exhaustion must be visible, never silently hidden. | Counters for I²S/DMA overrun, software ring-buffer overflow, USB short-write/timeout, frame drops. Unexpected non-zero counters fail a normal G1 run. | Requirement documented; physical evidence OPEN |
| MB-ACQ-07 | Device emits monotonic frame sequence and cumulative logical sample index. | Proposed uint32 frame_sequence increments per frame and wraps modulo 2³². Proposed uint64 first_sample_index starts at zero per stream session and advances by sample_count. Host detects gaps, duplicates, reordering and discontinuity. | B→C proposal |
| MB-ACQ-08 | Device exposes monotonic timestamp and timebase. | Proposed uint64 timestamp_us anchors the first sample to device monotonic microseconds; later frame times derive from anchor + sample index / 48,000. Host wall clock is not the continuity source. Measure uncertainty/drift later. | Proposal; measurement OPEN |
| MB-ACQ-09 | Device status/error telemetry is visible to host. | Minimum flags/counters: invalid configuration, I²S/DMA overrun, software buffer overflow, USB timeout/short write, stop reason, and host-detected sample/frame gap. STOP summary reports frames/samples and counters. | Exact bit assignments OPEN |
| MB-ACQ-10 | Wired USB path sustains 48 kHz mono streaming. | Identify the actual board connector/interface; on a 10 s test host parses exactly 480,000 logical samples with zero missing/duplicate samples. USB class and achieved throughput are not closed before joint review and physical test. | USB routing/class OPEN |
| MB-ACQ-11 | Host/device handshake occurs before audio starts. | Proposed HELLO_REQ/HELLO_ACK then START_REQ/START_ACK; device ACKs actual rate, channel count, encoding, protocol version and session ID. Unsupported/mismatched configuration is rejected. | B→C proposal |
| MB-ACQ-12 | Disconnect/reconnect starts a clearly identified new session. | New session ID/epoch on restart; sample index resets to zero within the session; host drops incomplete previous-session frames instead of concatenating them. | B→C proposal |

## 4. Initial framing / throughput proposal

A small binary frame over wired USB is proposed; CDC-ACM is the rapid-prototyping candidate, not a unilateral freeze.

Proposed v0 fixed header: 40 bytes, multi-byte values little-endian.

| Field | Size | Purpose |
|---|---:|---|
| Sync word “AUCF” | 4 bytes | Byte-stream resynchronization |
| protocol_version | uint8 | Draft version |
| frame_type | uint8 | HELLO / START / AUDIO / STATUS / STOP |
| header_length | uint16 | Proposed 40 |
| frame_sequence | uint32 | Per-session frame counter |
| first_sample_index | uint64 | First logical sample in frame |
| timestamp_us | uint64 | Monotonic timestamp anchor for first sample |
| sample_rate_hz | uint32 | 48,000 nominal |
| channel_count | uint8 | 1 logical channel |
| sample_encoding | uint8 | Proposed S32_LE |
| sample_count | uint16 | 256 for full frame; final frame may be shorter |
| payload_length_bytes | uint16 | For S32_LE, sample_count × 4 |
| status_flags | uint16 | Versioned status field |

Proposed S32_LE payload: each INMP441 24-bit two's-complement sample is decoded from the actual I²S slot, sign-extended to a signed 32-bit integer and serialized little-endian. Verify the actual I²S extraction in firmware. Full audio payload is 1,024 bytes/frame. At 187.5 frames/s the audio data is 192,000 bytes/s; a 40-byte header adds 7,500 bytes/s, about 199,500 bytes/s before any integrity trailer. This is an estimate, not a measured throughput.

CRC/checksum, exact USB class, version assignment and final field semantics remain OPEN for joint review. Exact synthetic sample comparison and continuity checks in G1 do not close the long-term application integrity decision.

## 5. ECM / ADC decision boundary

Kingstate KECG2740PBJ → bias/AFE → ADC → ESP32-S3 remains OPEN and does not block synthetic USB G1.

- ESP32-S3 internal ADC1 continuous/DMA is a bench candidate only. Its nominal 12-bit SAR resolution does not establish low-noise, linear or low-distortion PCG performance; test ADC/AFE-only noise separately.
- PCM1808-class external I²S ADC is a candidate only. Do not order or call it selected until exact module schematic, analog/digital supplies, MCLK/SCKI frequency/multiplier, BCLK/LRCK/DOUT, input coupling/full-scale, pinout and cost are checked and the advisor approves.
- Kaan / Module A owns AFE topology and phantom conditions; ADC architecture requires Module A + Module B + advisor input.

## 6. Evidence and handoff

Still required:
1. Actual board markings / PCB revision and matching schematic or routing evidence.
2. Identification of the USB connector/controller and host enumeration; mask unique identifiers.
3. Firmware source, commit SHA, binary SHA-256, ESP-IDF version and compile configuration.
4. Week-5 physical G1 synthetic stream and exact host numeric comparison.
5. Later microphone capture evidence: selected L/R slot, sample bit alignment/signedness, clock measurements and PCG-path measurements.

## 7. References

- [Direnc.net — purchased N16R8 board, seller code DSTK22852](https://www.direnc.net/esp32-s3-n16r8-wifi-bluetooth-board)
- [TDK InvenSense INMP441 datasheet](https://invensense.tdk.com/wp-content/uploads/2015/02/INMP441.pdf)
- [Espressif ESP32-S3-WROOM-1 / WROOM-1U datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf)
- [ESP-IDF I²S DMA documentation](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/i2s.html)
- [ESP-IDF USB Serial/JTAG documentation](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/usb-serial-jtag-console.html)
