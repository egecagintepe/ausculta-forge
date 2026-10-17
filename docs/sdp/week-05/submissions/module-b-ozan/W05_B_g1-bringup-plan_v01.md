# W05 Module B — G1 Firmware Bring-up Plan v1

**Owner:** Ozan — Module B, Embedded Acquisition & Data Path  
**Target window:** 2026-10-19 to 2026-10-25  
**Status:** PLAN ONLY — NO PHYSICAL G1 TEST HAS BEEN RUN OR PASSED  
**Dependencies:** board delivery/inspection, joint B→C protocol decision, Python host handshake support from Ege.

## 1. Objective

On the actually purchased ESP32-S3 N16R8 board, generate known synthetic samples, frame them, send them over the jointly selected wired USB device interface and numerically compare the host-received samples against the expected sequence. Initial G1 does not depend on microphone I²S or ECM ADC.

## 2. Before powering the board

1. Check the delivered seller/model marking against Direnc.net product code DSTK22852 and module designation ESP32-S3-WROOM-1-N16R8. Record the actual PCB revision only if marked or confirmed by a matching schematic.
2. Inspect connector labels and obtain matching board schematic/routing evidence. Identify the physical USB-C port routed to the chosen USB device controller. Do not assume this generic board is an ESP32-S3-DevKitC-1.
3. Use a known data-capable cable. Test candidate ports separately; record host enumeration, VID/PID and OS port name. The AUX audio cable is not a USB data cable. Mask unique serial/MAC identifiers from public logs.
4. Keep the microphone, ECM/AFE, phantom amp and speaker disconnected during the first USB-only bring-up.
5. Record host OS, board identity, cable/port and build environment.

## 3. Implementation sequence

### Stage A — build and identify

- Create a minimal ESP-IDF firmware project under firmware/ using the agreed USB controller and device class.
- Pin and record ESP-IDF and relevant component versions.
- Record commit SHA and firmware binary SHA-256.
- Confirm host enumeration and open the selected data interface. If only a USB-UART bridge enumerates, resolve connector mapping before claiming a Native USB test.

### Stage B — control handshake

- Implement the agreed HELLO and START/STOP subset.
- Return accepted rate, channel count, sample encoding, protocol version, session ID and firmware descriptor.
- Reject unsupported parameters explicitly.
- Keep USB writes in task context; no I²S/DMA ISR is needed for this synthetic-only test.

### Stage C — synthetic stream

- Generate 48,000 logical mono samples/s without enabling the microphone peripheral.
- First send a deterministic signed sample pattern that the Python host reproduces exactly; this tests framing, signedness, byte order and loss/duplicate detection.
- Next send a 100 Hz synthetic sine for 10 seconds; the host checks dominant frequency 100 Hz ±1 Hz and plots the waveform.
- Expected counts: 480,000 samples and 1,875 full AUDIO frames with 256 samples/frame.
- Proposed acceptance: every frame parses; exact deterministic sample comparison passes; zero missing/duplicate/reordered samples; zero unexpected device overflow, DMA or USB-timeout counters. Record actual duration/throughput rather than inferring them from USB's nominal line rate.

### Stage D — evidence capture

Store non-sensitive evidence in GitHub:
- Firmware source and build/run instructions.
- Board model/revision evidence sufficient to identify hardware; omit unique MAC/serial data.
- Connector/interface chosen and observed enumeration information.
- ESP-IDF / component versions, build command, firmware commit SHA and binary SHA-256.
- Raw host log and device log with sample/frame counts, sequence checks, timestamps and error counters.
- 100 Hz plot / analysis summary and machine-readable test result.
- Explicit PASS / FAIL / BLOCKED result for each criterion. Failed runs are still evidence and must not be rewritten as passes.

## 4. Hazards and non-dependencies

- On the N16R8 octal-PSRAM module, GPIO35–GPIO37 are reserved for memory interface and must not be allocated to I²S.
- ESP32-S3 silicon maps USB D− to GPIO19 and D+ to GPIO20, but physical connector routing on the purchased board remains unverified.
- INMP441 integration is later: 24-bit two's-complement, MSB-first I²S; 64 SCK cycles/WS frame; nominal supply 1.8–3.3 V; typical low-frequency −3 dB point 60 Hz. A synthetic USB pass does not mean the sensor acquisition path works.
- Do not finalize CRC, wire format or CDC-ACM/Vendor Bulk without Ege's review.
- ECM ADC architecture and PCM1808 approval are not G1 dependencies.

## 5. G1 pass boundary

G1 passes only after a physical ESP32-S3 board transmits the synthetic test over the agreed USB interface and the host logs the expected numeric sample sequence, sample count, frame continuity and zero unexpected error counters.

If board identity / USB route or protocol agreement is unresolved, mark the run BLOCKED and describe the missing evidence. This plan, a software-only simulation or a build without the board cannot be called physical G1 success. The later 30-minute stability test is a separate objective.
