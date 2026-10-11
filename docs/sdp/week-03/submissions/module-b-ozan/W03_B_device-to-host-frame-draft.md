# W03 Module B: Device-to-Host Frame Draft

**Week:** 3  
**Module:** B — Embedded Acquisition & Data Path  
**Owner:** Ozan  
**Status:** DRAFT COMPLETE — Week-3 closeout; wire format and acquisition settings are NOT FROZEN  
**Scope:** Documentation and interface draft only. No runtime firmware changes or physical measurements are claimed.

## 1. Objective

Record the Week-3 embedded acquisition architecture and conceptual Module B → Module C frame information needed for the Week-4 embedded-requirements freeze. This draft documents the current candidate architecture without treating unresolved ADC, USB-class, sample-packing, integrity or hardware-revision questions as final decisions.

## 2. MCU / Development-Board Candidate

- **Candidate:** ESP32-S3-DevKitC-1-N8R8.
- **Physical transport baseline:** wired ESP32-S3 Native USB.
- **Nominal acquisition baseline:** 48,000 samples/s, one PCG channel (mono).
- **Acquisition implementation direction:** sensor interface → peripheral acquisition (I²S or ADC) → DMA-backed buffering → continuity and acquisition-time metadata → USB device transport → PC ingestion.
- **Status:** board candidate identity is recorded in DW03-03. Supplier stock, exact shipped board revision and connector/cable type must be verified before order/at receipt. Firmware pin assignment and clock settings are Week-4 freeze items.

## 3. Embedded Data Paths

### 3.1 Digital MEMS path

`PUI DMM-4026-B-I2S-R` sensor on the `PUI DMM-4026-B-I2S-EB-R` evaluation board  
→ I²S (BCLK / WS / DOUT; exact physical EB pad mapping **OPEN**)  
→ ESP32-S3 I²S RX  
→ DMA-backed buffering  
→ monotonic sample continuity counter + device acquisition timestamp  
→ wired Native USB  
→ PC / Module C.

The raw sensor MPN and the purchased evaluation-board MPN have different roles:

- **Sensor under evaluation:** PUI DMM-4026-B-I2S-R.
- **Proposed bench carrier to purchase:** PUI DMM-4026-B-I2S-EB-R.

The evaluation board is documented as a solder-pad interface. Do not assume a fitted six-pin header or assign pin numbers from the draft Week-2 interface map until the actual pad functions and physical connections are confirmed from PUI documentation or inspection of the received board. A custom MEMS daughterboard is not a Week-3 requirement.

### 3.2 Analog ECM path

`Kingstate KECG2740PBJ`  
→ microphone bias + analog front end (AFE; MCP6022-I/P is a breadboard candidate, not a finalized gain/filter design)  
→ **ADC (OPEN engineering decision)**  
→ ESP32-S3  
→ DMA/buffering and continuity/timestamp metadata  
→ wired Native USB  
→ PC / Module C.

The ADC question is open because the project has not yet approved the exact digitization architecture. Options to evaluate:

1. ESP32-S3 internal SAR ADC1 as a **bench candidate only**. Its PCG noise, linearity, usable dynamic range, sampling behavior and repeatability must be measured; audio-grade characterization is not assumed.
2. An external I²S audio ADC such as **PCM1808 (candidate only)**. Before purchase, inspect the exact breakout/module schematic and verify its MCLK source, analog and digital supplies, input coupling, full-scale input compatibility, I²S format and local availability. Advisor/team approval is required before treating it as the selected architecture.
3. Department USB audio interface (C-05) as a separate reference/measurement route is not available in the lab per Ozan's audit. Ozan's personal 3.5 mm-to-USB dongle may be checked for exploratory recording, but its analogue input capability and signal path are unverified. Unless the advisor explicitly accepts that architecture, a PC sound-card recording does not replace the requested ECM → ADC → ESP32-S3 → USB → PC path.

No ADC has been declared FINAL.

## 4. Conceptual B-to-C Frame Information

The following is an **information contract**, not a frozen byte layout. Field order, offsets, integer widths where not already constrained, alignment, exact frame size, packetization and endian encoding must be agreed with Module C during Week 4.

| Conceptual field | Purpose / current rule | Status |
|---|---|---|
| Protocol / schema version | Allows the PC to reject an unsupported or incompatible device protocol before sample parsing. | Required concept; numeric version value OPEN |
| Message / frame type | Distinguishes sample data from handshake/control and status/error telemetry. | Required concept; exact values OPEN |
| Continuity counter / first sample index | Monotonic device-side sequence or cumulative sample index. Primary evidence for discontinuity; host USB arrival time does not establish sample continuity. Define rollover behavior. | Required concept; width/rollover OPEN |
| Timestamp | Device-side monotonic acquisition timestamp associated with the first sample in the payload (proposed convention). Document the tick clock/domain and units; do not substitute a host wall-clock timestamp. | Required concept; units and implementation OPEN |
| Sample count | Exact number of samples represented by the payload. | Required concept; fixed/variable frame count OPEN |
| Payload length | Number of payload bytes, or an equivalent unambiguous framing rule. | Required concept; exact wire field OPEN |
| Declared sample rate and channel count | Profile metadata to interpret payload; nominal baseline is 48,000 Hz and mono. | Baseline 48 kHz mono; final device/profile declaration freezes in Week 4 |
| Sample representation | Signed integer PCM is proposed. Week-2 interface requirements mention 24 meaningful bits in a 32-bit container for the digital-I²S baseline; that proposal is not yet the jointly agreed ECM/MEMS wire contract. Confirm signedness, meaningful bits, container width, alignment and endianness with Module C. | OPEN |
| Device / stream status flags | Identifies acquisition state such as ADC/I²S active, stream started/stopped, clock/synchronization state or mute condition where relevant. | Required concept; bit definitions OPEN |
| Error flags / counters | Reports detectable DMA/FIFO overrun, buffer overrun, sample discontinuity, I²S synchronization/clock fault, clipping where detectable, and integrity failure where applicable. Never silently hide a known internal loss. | Required concept; bit definitions OPEN |
| Integrity / CRC policy | Decide whether the application frame has CRC/checksum in addition to lower-layer USB checks; if selected, define algorithm, coverage, byte order and host failure behavior. | **DW03-09 OPEN — joint Module B/Module C decision** |
| Stream/session control | Clearly identifies start/stop and handshake/device capability or profile information where needed. | Message semantics OPEN |

### 4.1 Sample-rate and throughput baseline

- Nominal baseline: **48 kHz × 1 channel**.
- If the proposed 24-bit meaningful sample is carried in a 32-bit container, the sample-payload rate is:
  - 48,000 samples/s × 4 bytes/sample = **192,000 bytes/s** (before frame headers/status/integrity overhead).
- This is a calculation from the proposed representation, not a measured throughput result.
- If 24-bit samples are packed into 3 bytes/sample instead, the payload rate differs. Do not treat either packing scheme as final before Module B/Module C agreement.
- No legacy ~4 kHz acquisition target is used as the baseline in this draft.

## 5. USB Transport

- **Physical medium selected:** wired ESP32-S3 Native USB (DW03-08 closed for physical medium only).
- **USB device class:** **OPEN** — CDC-ACM versus vendor-specific Bulk must be assessed with Module C for host support, continuous-stream robustness, parser/resynchronization behavior and implementation effort.
- USB data transport is not replaced by BLE/Wi-Fi for the assessed core path.
- The exact USB device class, descriptors/endpoints and any transport-specific framing assumptions are Week-4 interface-freeze items.

## 6. Buffering, Continuity and Timebase — Week-4 Freeze Inputs

Current architecture direction:

1. Use peripheral-driven acquisition and DMA-backed circular or ping-pong buffering, not CPU polling as the continuous-sampling mechanism.
2. Assign a monotonically advancing sample index/counter at the acquisition boundary (or at an explicitly documented equivalent boundary).
3. Associate a device monotonic timestamp with acquired data; explicitly document what event/sample it timestamps and the clock units.
4. Count and report internal overruns/drops. Do not infer continuity solely from how quickly the PC receives USB transfers.
5. Size DMA/stream buffers after choosing the acquisition path, frame payload, transport class and latency budget. Exact buffer size, packet samples and scheduling priorities are **not frozen in Week 3**.

## 7. Week-3 Decision Status

| Decision | Status | Week-3 resolution |
|---|---|---|
| DW03-03 — MCU development board | CLOSED for candidate identity | ESP32-S3-DevKitC-1-N8R8; physical revision/stock/cable type remain procurement checks. |
| DW03-08 — B-to-C physical transport medium | CLOSED for physical medium only | Wired Native USB. This does not select the USB class. |
| DW03-09 — application integrity/CRC | OPEN | Joint Module B/Module C decision; do not close without owners' agreement. |
| DW03-10 — sample representation | OPEN | 48 kHz mono baseline retained; signed 24-bit-in-32-bit is a proposal, not final agreement. |
| DW03-12 — USB device class | OPEN | CDC-ACM vs vendor-specific Bulk. |
| DW03-13 — ECM external ADC path | OPEN | Internal ADC1 bench candidate vs externally clocked I²S ADC candidate; C-05 is unavailable in the department lab. Advisor decision and hardware evidence required. |
| DW03-14 — lab equipment audit | CLOSED (availability status only) | Scope, function generator, DMM, soldering station and reusable breadboards/dev-boards reported available by Ozan; C-05 unavailable in the department lab. This is not a calibration claim. |
| DW03-15 — personal 3.5 mm-to-USB dongle suitability | OPEN | Exact model and input capability need inspection; not assumed to be a calibrated C-05 equivalent. |

## 8. BOM / Week-4 Order Readiness Snapshot

This is a readiness snapshot, not purchase authorization. Current component candidates and quantities must be rechecked against the live sourcing workbook and supplier pages before order.

| Item | Current candidate / planned quantity | Readiness / action |
|---|---|---|
| MCU development boards | ESP32-S3-DevKitC-1-N8R8 × 2 planned (Group-A requirement) | Candidate identified. Confirm current stock, exact shipped board revision, Native USB/UART connector types and cable compatibility. |
| ECM microphones | Kingstate KECG2740PBJ × 4 proposed (two needed signal-carrying units plus two spares) | Candidate identified. Confirm current price, stock, delivery and order quantity at checkout. |
| MEMS evaluation boards | PUI DMM-4026-B-I2S-EB-R × 2 planned | Evaluation-board MPN identified. Confirm current price/stock/delivery and actual pad mapping; no six-pin fitted header assumed. |
| MEMS sensor identity | PUI DMM-4026-B-I2S-R (sensor mounted on EB-R) | Keep distinct from the purchased EB-R carrier in BOM/documentation. |
| ECM AFE / op-amp | MCP6022-I/P is a breadboard candidate; Group-A op-amp quantity requirement is 5 | Confirm exact package/footprint and datasheet suitability. Bias, gain and filter values remain measurement/design decisions; do not claim finalized AFE. |
| ECM ADC | ESP32-S3 SAR ADC1 bench candidate; PCM1808 external I²S ADC candidate; C-05 or an input-capable USB sound dongle as possible separate exploratory/reference route | **OPEN.** Do not purchase PCM1808 until the exact module, clock/power/interface details and advisor acceptance are confirmed. C-05 is not available in the department lab; personal dongle suitability remains OPEN under DW03-15. |
| Dedicated low-noise LDO | Not included as a mandatory Group-A/core purchase. The supplied `SDP4_Component_Requirements_EN.docx` places a low-noise regulator in Group B (can wait until Semester II). | First measure rail noise and acquisition SNR. A purpose-built low-noise module (e.g. LP5907-based, with exact breakout MPN/schematic verified) may be an optional bench aid if justified; do not describe AMS1117 as a low-noise substitute. Do not add a regulator without checking output voltage/current, input/output headroom and powering arrangement. |
| Phantom exciter | Motorobit 30 mm / 12 Ω vibration speaker proposal | Kaan to confirm compatibility and useable 20–500 Hz phantom excitation; consider alternate only if justified. |
| Phantom amplifier | PAM8403 mini-amplifier module proposal | Confirm exact module schematic, power source, proposed-load compatibility, input coupling and cable arrangement. |
| Silicone / coupling | Transparent silicone sheet; nominal 3 mm is only a starting proposal | Kaan to confirm hardness, contact geometry, compression and quantity. |
| Rigid frame | Acrylic, nominal 3 mm / 20 × 30 cm starting stock proposal | Kaan to freeze geometry, mounting repeatability and clamp arrangement. |
| Breadboards / jumpers | Required Group-A prototype consumables | Confirm quantity; also provide compatible headers and hookup wire for solder-pad evaluation-board connections. |
| Shielded cable / connectors | Exact cable and connector types not fully frozen | Confirm ECM two-wire interface and required audio/bench connectors. Do not infer an XLR cable is directly suitable for the ECM. |
| USB data cables | Two data-capable cables planned: one for Native USB, one for USB-to-UART/logging | Espressif's ESP32-S3-DevKitC-1 v1.1 guide specifies a USB 2.0 Standard-A-to-Micro-B cable and warns against charge-only cables. Plan two data-capable cables for the two-port workflow; inspect the delivered board's revision and both physical port connectors before placing the cable order. [Espressif DevKitC-1 v1.1 guide](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html). |

### 8.1 Department lab equipment audit

**Audit status: availability reported by Ozan on 2026-10-12.** The entries below record availability only; they do not certify calibration, bandwidth, noise floor, or measurement performance.

- Oscilloscope / DSO — **REPORTED AVAILABLE IN DEPARTMENT**
- Function generator / waveform generator — **REPORTED AVAILABLE IN DEPARTMENT**
- Digital multimeter — **REPORTED AVAILABLE IN DEPARTMENT**
- Soldering station — **REPORTED AVAILABLE IN DEPARTMENT**
- Reusable breadboards / lab development boards — **REPORTED AVAILABLE IN DEPARTMENT**
- USB audio interface / sound card — **NOT AVAILABLE IN DEPARTMENT LAB**

Ozan reports having a small personal 3.5 mm-to-USB audio adapter. Its exact model and direction of conversion are not yet inspected. Confirm that it has an analogue **input** (not only USB-to-headphone/DAC output) and inspect input range/coupling, microphone bias, gain/AGC and supported sampling formats before considering it for exploratory recording. Until then it is **NOT VERIFIED as a substitute for C-05 or as a calibrated reference instrument**. See DW03-15 in the [Week-3 decisions](../decisions.md).

### 8.2 Week-4 order gate blockers

Before calling BOM v1.0 purchase-ready:

1. Confirm the exact MCU board SKU, revision-sensitive connector/cable set, stock and delivery.
2. Confirm the PUI EB-R sourcing and real pad/interface mapping.
3. Resolve or obtain advisor disposition for the ECM ADC architecture; decide whether C-05 is available as a reference route.
4. Confirm the candidate AFE/op-amp package and the first breadboard topology, while leaving untested gain/filter values explicitly TBD.
5. Kaan to confirm exciter/amplifier compatibility, silicone/coupling and rigid-frame details.
6. Lab availability audit has been recorded from Ozan's report: scope, function generator, DMM, soldering station and reusable breadboards/dev-boards reported available; department USB audio interface unavailable. Recheck live supplier price/stock/delivery data, and inspect the personal audio dongle only if the team wants to use it for exploratory capture (DW03-15).

Do not let open ADC or USB-class decisions silently become FINAL through a BOM row. Any approved deviation from the instructor's list must be recorded in the Week-3/Week-4 decision log.

## 9. Evidence and References

- [Week-02 B-to-C interface requirements](../../week-02/bc-interface-requirements.md) — baseline 48 kHz mono, conceptual frame information and Module C ingestion requirements.
- [Week-02 meeting brief](../../week-02/meeting-brief.md) — Module B ownership, hardware-to-host path, sourcing and lab-audit expectations.
- [Week-03 decisions](../decisions.md) — authoritative record for DW03-03 and DW03-08 through DW03-15.
- [Week-03 Module A candidate-selection note](../module-a-kaan/W03_A_transducer-candidate-selection.md) — current ECM/MEMS/exciter proposals.
- [Week-04 Module B embedded-requirements freeze placeholder](../../week-04/submissions/module-b-ozan/W04_B_embedded-requirements-freeze.md) — next handoff deliverable.

No physical bench results, signal-quality values, continuity test results, throughput validation, or lab availability claims were generated by this documentation closeout.

## 10. Week-4 Handoff

Module B's Week-4 tasks are:

- Freeze the nominal acquisition profile: 48 kHz mono baseline, exact peripheral/input, sample representation, and clock configuration.
- Freeze DMA/buffering policy and buffer size with a reasoned latency/overrun budget.
- Freeze timestamp meaning/timebase and monotonic continuity-counter width/rollover semantics.
- Calculate and validate expected payload and protocol throughput.
- Freeze status/error reporting and agree with Module C on frame/sample representation and integrity policy.
- Make BOM v1.0 purchase-ready using verified supplier data and documented lab-audit results.
- Prepare the Week-5 known/synthetic stream so the end-to-end MCU-to-PC path can be demonstrated without depending on the acoustic phantom.
