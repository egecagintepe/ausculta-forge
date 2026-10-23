# First Contact release — 2026-10-23

**SOFTWARE VERIFIED. COMPILED BUT NOT FLASHED. HARDWARE NOT TESTED.**

`PHYSICAL_HARDWARE_BRINGUP: NOT_EXECUTED`

Physical G0/G1A/G1B/G1C/G2/G3: **PENDING**. No identified ESP32 was opened, flashed
or measured. The only enumerated ports were an unrelated Prolific PL2303 bridge
and Intel SOL. They were not probed or treated as AuscultaForge.

Release artifact source: **93b95c764f606c2d679e69b158e2e3ce4f3441b4**, a clean source
tree at build time (only ahead-of-origin metadata in git status). Later delivery
commits add evidence/documents, not a different firmware source. Milestones:

- c76396a: interface audit and purchased-board dossier.
- d53c498: independent, reviewed-profile I2S DMA adapter and source accounting.
- f0413cf: safe workflows, shared strict acceptance, Device Center/API integration.
- 44c5754: failed-run evidence and port release after handshake/STOP failure.
- 93b95c7: day-one/electrical runbooks and current versus historical status.

Ege owns software/firmware integration, Kaan physical assembly/acoustic work,
Ozan acquisition/embedded peer review where appropriate. No unperformed physical
contribution is assigned to anyone.

## Delivered entry points

| Deliverable | Location / behavior |
| --- | --- |
| Contract audit | [FIRST_CONTACT_CONTRACT_AUDIT.md](FIRST_CONTACT_CONTRACT_AUDIT.md), baseline PASS/FAIL and responsible fixes |
| Board identity | [BOARD_DOSSIER_DSTK22852.md](BOARD_DOSSIER_DSTK22852.md), confirmed/likely/inspection-required facts |
| Day-one quickstart | [DAY_ONE_LAB_RUNBOOK.md](DAY_ONE_LAB_RUNBOOK.md), beginner steps, engineering gates and recovery appendix |
| Electrical/G2/G3 plan | [INMP441_FIRST_ACQUISITION.md](INMP441_FIRST_ACQUISITION.md) |
| Passive preflight | `tools/hardware/preflight.py`, `windows_preflight.ps1`: JSON + readable status; no port opens |
| Guided CLI | `tools/hardware/bringup.py`: preflight, build, identify, flash, hello, physical-only g1 |
| Production session | `software/pcg_app/canonical/engine.py`, shared `acceptance.py` policy; no parallel wire implementation |
| Evidence exporter | `software/pcg_app/hardware_workflow.py`, CLI session folders and Desktop ZIP endpoint |
| Desktop | Existing Device Center: deliberate port choice, firmware/identity, live counters, automatic orderly G1 STOP, failure evidence and export |
| I2S | `firmware/main/i2s_source.c`; default-disabled reviewed board profile, explicit portable slot conversion |

Scan/access never establishes firmware identity. HELLO verifies nonce, protocol and
capabilities; G1 checks firmware compatibility, exact configuration, all samples,
frames, CRC, sequence/index/time, parser state, host ingestion and final telemetry.
The default build supports source 1. Source 0 is enabled only through the reviewed
board profile; live data is never replaced by synthetic data. Source modes 0/1
remain visibly distinct from the simulator.

The prior partial 2048-sample Desktop test is now correctly a failed **full G1**,
even if its handshake/stream/STOP lifecycle was clean. A CRC-valid frame, a queue
counter or an enum describing an open port cannot independently produce a pass.

## Actual firmware build and artifacts

Pinned inputs: ESP-IDF **5.5.1**, Xtensa **esp-14.2.0_20241119 / GCC 14.2.0**,
esp_tinyusb **2.2.0**, tinyusb **0.19.0~3**, target **esp32s3**. The original real
dependency lock is preserved. Tools/Python environment were installed locally
under ignored `firmware/build`; no global PATH, driver or Windows setting was
changed. Session-local official IDF export was used.

The build workflow actually executed `idf.py set-target esp32s3 build` on first
configuration, then `idf.py -B ... reconfigure build` for the final committed
source. It checked 16 MB flash, octal PSRAM/80 MHz and a sensor-free default boot
configuration. **Physical boot and actual PSRAM capacity are not established by
these configuration checks.**

| Artifact | Actual result |
| --- | --- |
| Default G1 image, firmware 1.1.0 | ESP-IDF build PASSED, source_modes=[1], NOT FLASHED |
| Reviewed-profile I2S code path | Separate ESP-IDF build PASSED, NOT FOR FLASHING with provisional 4/5/6 pins |
| G1 application SHA-256 | `af1dfc4011291a768868ca3058b621f32191569c2f6ddf55862dcbfc48c55397` |
| I2S compile-check application SHA-256 | `19ac3cf5fa0a381f22d7c7be75e881bb668ef29b0de027f7c788c851d90b0347` |

Preserved local compiled baseline:
`firmware/build/releases/93b95c7-g1/`. It contains bootloader, partition table,
application, exact sdkconfig/lock/layout, build description/flash args, a matching
manifest and hashes. It remains separate from future microphone builds. This is
a known compiled configuration, **not a physically proven bootable release**.
The binary files are local ignored artifacts, not committed source files.

The checked-in [build manifest](../../../firmware/evidence/first_contact/firmware_build_manifest.json)
records all binary hashes, actual compiler, source commit, timestamp, source modes,
memory expectations and partition layout. It points at the preserved local
baseline. The [I2S compile manifest](../../../firmware/evidence/first_contact/i2s_compile_manifest.json)
is explicitly rejected as a flashable release. Actual
[G1 build output](../../../firmware/evidence/first_contact/g1-idf-build.txt) and
[I2S build output](../../../firmware/evidence/first_contact/i2s-idf-build.txt) are retained.

To select the preserved baseline later, append
`--manifest firmware/build/releases/93b95c7-g1/firmware_build_manifest.json`
to the `bringup.py flash` or `g1` command. The default g1 CLI requires a successful
local build manifest and compares its version with HELLO. If a ROM identity file
from flashing is available, it also compares reported UID with that board's MAC
suffix. This links observations; it is not cryptographic image authentication.

## Executed validation gates

| Gate | Result / retained evidence |
| --- | --- |
| Python host, DeviceRuntime, recording/DSP, diagnostics, ML service, new workflows, firmware host tests, canonical and fault-injection acceptance | **577 PASSED**, 0 failed/errors/skipped, 49.51 s; [output](../../../firmware/evidence/first_contact/python-tests.txt), [JUnit](../../../firmware/evidence/first_contact/python-tests.xml) |
| Portable C protocol/CRC/control/parser/PCM and 500000-sample SPSC concurrency | **7 C suites PASSED**; [output](../../../firmware/evidence/first_contact/c-protocol-tests.txt) |
| Firmware core / cross-language golden vectors | PASSED within the Python gate; 480000 C-generated samples, 1875 frames, real production Python decoder, normative values/timestamps and STOP telemetry |
| Production engine software fault handling | PASSED: no simulated physical pass, incomplete/extra data, corrupt/gapped/duplicated frames, bad telemetry/version, STOP timeout, ingestion rejection, restart, fresh IDs, live-validator separation |
| Flash safety software checks | PASSED: absent port, tampered artifact and missing explicit write confirmation cannot write firmware |
| Frontend unit tests | PASSED; [output](../../../firmware/evidence/first_contact/frontend-unit.txt) |
| TypeScript `tsc --noEmit` | PASSED; [output](../../../firmware/evidence/first_contact/frontend-typescript.txt) |
| Vite production build | PASSED; [output](../../../firmware/evidence/first_contact/frontend-build.txt) |
| Tauri/Rust | **6 PASSED**; [output](../../../firmware/evidence/first_contact/rust-tests.txt) |
| Windows preflight, board absent | PASSED as a diagnostic run: NOT_DETECTED, IDF/build/host/backend READY in exported shell, hardware NOT_EXECUTED; [JSON](../../../firmware/evidence/first_contact/preflight-board-absent.json) |
| Evidence and preserved binary SHA-256 self-check | PASSED; evidence bytes protected from Git line-ending normalization |
| Physical flash, boot, USB throughput, G1, I2S clocks/microphone and acoustics | **NOT_EXECUTED** |
| Installer/package rebuild and real interactive Desktop/board test | SKIPPED: packaging source unchanged; no identified board; unit/type/build/Rust gates are not a physical Desktop acceptance |

Commands (repository root unless noted):
```powershell
.\.venv\Scripts\python.exe -m pytest software/tests firmware/tests tools/protocol_lab/python/test_canonical_protocol.py tools/protocol_lab/python/test_physical_acceptance_gates.py -q
.\tools\hardware\windows_preflight.ps1 -Output firmware/build/preflight.json
.\.venv\Scripts\python.exe tools/hardware/bringup.py build
# in software/frontend:
npm test
npm run lint
npm run build
# repository root:
cargo test --manifest-path software/frontend/src-tauri/Cargo.toml --locked
```

Non-fatal warnings: existing Starlette/httpx deprecation, Torch JIT deprecation,
and Vite's existing >500 kB chunk notice. They are not hidden test failures and
do not justify unrelated dependency/packaging migrations in this operation.

## Smoke scenario coverage and physical follow-up

| Scenario | Software behavior verified / physical follow-up |
| --- | --- |
| Board absent / unknown COM / wrong connector / cable disconnected | Passive scan and explicit selection; no inference of cable quality or device damage; actual cable/connector tests pending |
| Busy/permission error / firmware absent / bad HELLO nonce/version/capabilities | Explicit connection failure, Flight Recorder and port release; no simulation fallback; actual Windows driver-lock exercise pending |
| Normal G1 / corrupt, duplicated or lost frame / sample mismatch | Strict shared acceptance; exact counts, first mismatch and checksum; physical run pending |
| Missing STOP_ACK / disconnect / device restart | Failed evidence, bounded deadlines, preserved recording and fresh HELLO/session; physical unplug/re-enumeration pending |
| Firmware ring/USB pressure / host ingestion failure | Counters retained and reconciled; rejected samples cannot produce a pass; actual sustained 200250 B/s and MCU health pending |
| App/session restart / re-enumeration / wrong firmware version | Software lifecycle/version regression passed; OS/device integration remains a physical checklist item |
| Unsupported I2S / absent microphone / zeros | Default source 0 rejection and explicit slot conversion tested; no fake data; zero/silence is not proof of mic presence, electrical G2 mandatory |
| Recording/reopen/raw DSP/decimation/evidence export | Existing recording/scientific tests plus new export/hash checks pass; real sensor provenance/sample-count/clock review pending |

Every exported run contains session, board/build identity, enumeration, protocol,
integrity, telemetry and timing JSON, Flight Recorder JSONL, an advisor-readable
report and file hashes. Unavailable build/board/instrument values are labeled,
not guessed. Unrelated workstation device identifiers are omitted from the public
board-absent release record; the original local preflight remains under build.

## Exact next laboratory steps and blockers

Ege and Kaan first complete G0 photographs, module/header/connector/power routing
and ROM identity, then explicit-confirmation flashing and observed boot. Ege runs
Desktop HELLO/full physical G1 and exports its independent evidence. Kaan may then
assemble the reviewed single-INMP441 connection, measure 3.3 V and clocks, and
work with Ege on a separate source-0 build/flash/raw-WAV qualification. Ozan can
review acquisition/alignment and evidence.

Unresolved physical facts: actual PCB revision/manufacturer schematic, connector
routes, bridge chip, power isolation/VBUS sensing, header orientation and safe mic
pins; actual boot/PSRAM health, USB timing/throughput, DMA stability, supply/clock
measurements and microphone response. A physical breadboard diagram is deliberately
pending actual board revision confirmation. No clinical or low-frequency PCG claim,
no automatic MurmurMIL inference on this sensor domain.
