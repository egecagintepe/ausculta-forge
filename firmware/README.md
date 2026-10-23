# AuscultaForge ESP32-S3 deterministic G1 firmware

Ownership: Ege and the AuscultaForge team. This is an ESP-IDF application for the
purchased ESP32-S3-WROOM-1-N16R8, not an Arduino/UART demonstration. Read the
[wire audit](PROTOCOL_AUDIT.md) before changing protocol code.

**Current delivery: SOFTWARE VERIFIED; COMPILED BUT NOT FLASHED; HARDWARE NOT TESTED.**
**PHYSICAL G1 PASSED: PENDING.** See [First Contact release](../docs/engineering/hardware/FIRST_CONTACT_RELEASE.md).
The earlier [G1 evidence](EVIDENCE.md) is the historical 2026-10-22 host-only baseline.

## Pinned build inputs

- ESP-IDF **v5.5.1**, target `esp32s3`.
- IDF-selected Xtensa compiler **esp-14.2.0_20241119**, GCC 14.2.0.
- Managed `espressif/esp_tinyusb` **2.2.0** and `espressif/tinyusb` **0.19.0~3**.
- 16 MB flash, DIO 80 MHz; 8 MB octal PSRAM 80 MHz. These are module settings,
  not a claim that the purchased PCB and power supply have been verified.
- Explicit fixed versions are in `main/idf_component.yml`; the genuine
  hash-bearing `dependencies.lock` was generated with Espressif Component Manager
  2.4.11 for declared IDF 5.5.1 / esp32s3. This standalone dependency resolution
  does not imply that ESP-IDF or its cross compiler is installed. Preserve and
  review the lock during the first real `idf.py build`.

Sources used to verify APIs and versions:
[esp_tinyusb 2.2.0 source](https://github.com/espressif/esp-usb/tree/c04934a51fb0f4db4b63b2500af793d1c0abf742/device/esp_tinyusb),
[official CDC example](https://github.com/espressif/esp-idf/blob/master/examples/peripherals/usb/device/tusb_serial_device/main/tusb_serial_device_main.c),
[component migration](https://github.com/espressif/esp-usb/blob/c04934a51fb0f4db4b63b2500af793d1c0abf742/docs/device/migration-guides/v2/tinyusb_cdc_acm.md),
[IDF toolchain versions](https://github.com/espressif/esp-idf/blob/v5.5.1/tools/tools.json).
The IDF v5.5.1 bundled example still uses compatibility APIs; this application
uses the managed component's current `tinyusb_cdcacm_init` and default config API.

## Source tree

```text
firmware/
  CMakeLists.txt                 ESP-IDF project / version and target gate
  sdkconfig.defaults            N16R8, UART console, CDC buffers, 1 kHz RTOS
  dependencies.lock             real registry resolution, exact component hashes
  partitions.csv                factory app; no OTA or persistent recordings
  main/
    idf_component.yml           exact component requirements
    CMakeLists.txt
    app_main.c                  entry point, one owner task, UART state logs
    usb_transport.[ch]          real TinyUSB CDC, line events, partial TX retry
    board_config.h              SoC USB mapping; I2S pins deliberately unassigned
  components/g1/
    CMakeLists.txt              compiles existing lab packet_framing.c in place
    g1.c / include/g1.h         command parser, queue, session, pacing, telemetry
    acquisition.c              normative source 1; live source explicitly rejected
    include/acquisition.h      bounded task-context acquisition seam
  tests/
    bridge.c                   host test ABI around actual firmware core
    test_g1.py                 real Python decoder/session/acceptance validator
    golden_vectors.json        frozen HELLO/START/AUDIO/STATUS/STOP/ERROR bytes
    make_goldens.py             independent struct/CRC oracle
  PROTOCOL_AUDIT.md
  EVIDENCE.md
```

## Build, flash and recovery

Follow the [Windows physical bring-up guide](../docs/engineering/hardware/FIRST_PHYSICAL_USB_BRINGUP_GUIDE.md).
From an exported **ESP-IDF v5.5.1** PowerShell, in this directory:

```powershell
idf.py --version
idf.py set-target esp32s3
idf.py build
```

Save the real build log, `build/project_description.json`, `sdkconfig`,
`dependencies.lock`, `build/flasher_args.json`, and the firmware binary SHA-256.
Review that the lock remains at exactly the pinned versions.
A successful host GCC test is not an ESP32 build. Do not flash until the board,
connector, chip identity, flash size, power routing and selected COM port have
been positively identified. No eFuse operations are needed.

## Host tests

From repository root, with existing Python test dependencies and GCC in PATH:

```powershell
.venv\Scripts\python.exe -m pytest firmware/tests -q
.venv\Scripts\python.exe -m pytest tools/protocol_lab/python/test_canonical_protocol.py -q
```

Tests compile the real C session and shared canonical serializer as a host shared
library with `-std=c11 -Wall -Wextra -Werror -O2`, then pass its bytes through the
unchanged production Python host. The 10-second test uses the existing acceptance
validator with `is_physical=False` and the workstation monotonic clock. Virtual
time tests additionally check release deadlines and every one of 480,000 samples.

## Runtime contract

One FreeRTOS session task owns all session/parser/queue state. Espressif starts a
separate TinyUSB task. Callbacks only publish atomic line/link state. Streaming
allocates no memory. SDK startup allocates its own driver/task buffers once.
The app never deletes a task that owns a queue; close, detach, suspend and timeout
reset session state and require HELLO before another START. Hardware reset is the
full service restart path; this project has no runtime driver replacement API.

State order: BOOT -> USB_READY -> HELLO_COMPLETE -> READY -> STARTED -> STREAMING
-> STOPPING -> COMPLETE. HELLO_COMPLETE is the validated handshake transition;
READY follows after its reply is enqueued. STARTED includes queued START_ACK;
FIFO ordering keeps it ahead of AUDIO. Only valid START begins production.
DTR must be asserted; RTS and virtual baudrate do not pace USB.

A complete 256-sample block is released after `t0 + floor((n+256)*1e6/48000)`.
At most one block is produced per 1 ms owner-task tick. The first frame timestamp
is `t0`; later timestamps use the normative first-sample formula. The 480,000th
sample is released at 10 seconds. These synthetic deadlines do not measure I2S
clock accuracy. Targets 1..480000 are supported (short final blocks allowed);
continuous and larger acquisitions are rejected by this G1 firmware.

The application TX FIFO holds eight 1068-byte slots; AUDIO uses at most six,
leaving control capacity. Every byte offset survives a short USB write. RX is a
60-byte command-only sliding parser; TinyUSB RX/TX/endpoint FIFOs are 4096 bytes.
RX is serviced before up to four TX attempts each tick so STOP cannot be starved
by AUDIO. Bad version/count/format/opcode frames and CRC failures are discarded
and counted without responding to noise. An incomplete command expires after
1 second without RX progress. Endpoint RX backpressure uses the stack's bounded
FIFO; there is no callback queue silently dropping STOP requests.

No TX progress for 1 second aborts the session and clears pending app/USB FIFO
bytes. A session expires after 40 seconds if STOP never completes. Recovery is
close/reopen, HELLO, START; the host's decoder must resynchronize after a truncated
packet. A rapid close/open may discard bytes at the reset boundary: retry HELLO
if the first probe times out. DTR close, detach and suspend invalidate the session;
resume does not restart acquisition. Default PHY setup is bus powered: do not
power independently through a second port without confirming VBUS sensing/routing.

At target, generation stops and waits for host STOP_REQ. STOP is honored even
with queued AUDIO. STOP_ACK is created after the application queue and TinyUSB
software FIFO are empty; USB preserves byte order for any in-flight endpoint
transfer. "Flushed" means handed to USB, not proof that the host accepted it.
Final host sample counts and CRC are mandatory evidence. Repeated STOP for the
completed session returns the same totals. A subsequent START gets a new nonzero
session counter seeded at boot from the ESP RNG. Across boots uniqueness is
probabilistic; no flash or eFuse counter is written.

`generated_samples` includes generated-but-dropped blocks; `fully_queued_samples`
counts complete AUDIO blocks accepted by the application FIFO; `audio_bytes_queued`
counts their complete wire bytes, including header/CRC (1875*1068 for G1). The
counters do not claim delivery. Full AUDIO FIFO increments dropped samples and
ring overflow events, preserves indexing/sequence gaps, and marks later frames.
STATUS is attempted every 188 blocks. STOP_ACK snapshots final partial-write,
timeout/disconnect and drop counters. Parser CRC/malformed/control-overload counts
are local diagnostics in G1Session; the canonical telemetry has no such fields,
so the wire layout is preserved. Command flooding beyond eight pending responses
aborts rather than overwriting queued packets.

Local ERROR codes: 1 invalid state, 2 unsupported source, 3 session mismatch,
4 unsupported configuration, 5 transport fault, 6 I2S acquisition fault (retained in final diagnostics).
Canonical v0.1 defines no shared enum for these numbers. Source 0 is rejected without the reviewed board profile; source 2 is always rejected,
HELLO advertises only Profile B + LSB encoding, capability_flags=0 (undefined
feature bits are not guessed). HELLO echoes a 32-bit nonce; the host validates it.
START has no nonce field. Binary CDC is never used for printf or ESP logs.

## Reviewed-profile I2S acquisition

Firmware 1.1.0 implements source 0 using the IDF 5.5.1 standard I2S RX driver,
a separate DMA reader task and bounded eight-block queue. It is disabled by
`AF_I2S_CONFIRMED_PROFILE` unless the actual PCB pins and electrical connections
have been reviewed. Default firmware still supports G1 source 1 only, and boots
without a microphone. HELLO does not invent source capability bits.

`acquisition_register_live/start/block/stop` is the independently testable source
boundary. `pcm24_from_i2s` explicitly converts the 24 meaningful MSB slot bits to
signed LSB S32LE. Source 0 never falls back to synthetic data. Completed source
blocks discarded at STOP are reported as drops; unknown DMA sample losses are
reported as overflow/error events, not an invented sample count. First-sample
live timestamps are estimates from observed block completion and nominal duration.

See [INMP441 electrical/qualification plan](../docs/engineering/hardware/INMP441_FIRST_ACQUISITION.md)
and [day-one runbook](../docs/engineering/hardware/DAY_ONE_LAB_RUNBOOK.md).
The I2S-enabled compile-check image uses provisional pins and is NOT FOR FLASHING.
Physical G2/G3 remain NOT_EXECUTED.
