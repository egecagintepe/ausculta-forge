# Morning hardware integration release candidate — 2026-10-23

**SOFTWARE VERIFIED; COMPILED BUT NOT FLASHED.**
`PHYSICAL_HARDWARE_BRINGUP: NOT_EXECUTED`. H0–H5 remain NOT_EXECUTED.

Start here: [Türkçe sabah rehberi](../hardware/START_HERE_TOMORROW.md).

## Release identity

- Starting local/remote main: `6aadccfcc5f4c401bdf18638ea343d705a41c0d1`.
- Final executable source and validation commit: **`3df4ba8ccbdf2e4d3695399a1c315df4c0d0e475`**.
- `8926689`: runtime/USB/recording fixes, packaging inputs, CLI extensions and tests.
- `9788d74`: Turkish operator documents, laptop setup, electrical plan and review.
- `3df4ba8`: supported I2S start failure reports acquisition error6, with C regression proving independent G1 recovery.
- The following delivery commit adds this report and compact evidence only.
  Resolve its exact identity with `git log -1 --format=%H -- docs/engineering/release/MORNING_RELEASE_REPORT.md`;
  the final user handoff records that delivery SHA. A commit cannot contain its own hash.

Existing main checkout only; no branch/worktree, destructive reset, force push,
hardware write, driver install or model retraining. No raw medical recordings,
weights, bulky logs or new machine-specific absolute paths enter this delivery.
Historical predecessor evidence is retained, not silently rewritten.

## Changes and review

See [baseline findings](MORNING_BASELINE_AUDIT.md) and
[eight-layer/protocol/failure-matrix review](MORNING_INTEGRATION_AUDIT.md).

| Files / group | Concrete result |
| --- | --- |
| software/pcg_app/canonical/{engine,session,transport,acceptance}.py | Guaranteed worker teardown, released partial-open handle, firmware compatibility before READY, explicit simulator/firmware diagnostic origins, shared acceptance and errors |
| software/pcg_app/{app,state}.py | Refuse replacing unclosed USB owner; orderly shutdown; thread-safe bounded display coalescing; raw recording before DSP; STOP finalization; DSP reset on new session; storage finalization failure invalidates G1 evidence |
| software/pcg_core/recording.py | RLock protects start/append/stop; refuse overwriting an existing session directory |
| software/{requirements.txt,pyproject.toml,build_desktop_backend.py,auscultaforge-backend.spec} | pyserial/PyWavelets declared, portable spec, Windows serial modules included, generated spec stays in ignored work directory |
| tools/hardware/{bringup,preflight}.py; software/pcg_app/hardware_workflow.py | Existing CLI gains doctor/watch/boot-log/qualify; useful dependency-absent checker; actual build/saved config/hash/security gates; validated raw screen |
| software/frontend/{package.json,src/components/DeviceView.tsx,src/tests/device_first_contact.test.ts} | Tested physical/simulation/failure labels, no device inferred from simulator-only list, automatic STOP applies to live target too |
| firmware/tests/{make_goldens.py,golden_vectors.json,test_g1.py}; software/tests/{test_morning_release,test_first_contact,test_usb_integration_bridge}.py | Byte-level C edge/wrap/partial/truncation oracles; 26 additional tests over baseline; tighten simulated recording provenance expectation |
| README.md; firmware/{README,BUILD_AND_FLASH,RELEASE_READINESS}.md | Current entrypoint, pinned build/recovery and evidence boundaries |
| docs/engineering/hardware/{START_HERE_TOMORROW,WINDOWS_LAPTOP_SETUP,LAB_SESSION_01_PLAN,PRELIMINARY_PIN_PLAN,PHYSICAL_INSPECTION_CHECKLIST,INMP441_FIRST_ACQUISITION}.md | Turkish morning sequence, laptop setup, team/procurement plan, separate conditional wiring and physical confirmation, executable G2 screen |
| docs/engineering/release/MORNING_* | Baseline, integration review, this report, reusable gate matrix and compact measured verification summary |

No production firmware wire/layout/formula change was required. C code was
reviewed against actual host source and rebuilt, not inferred from prior reports.

## Executed gates

| Gate | Status | Evidence (repo-relative; large local products stay ignored) |
| --- | --- | --- |
| S0 repo/environment | PASS | Starting snapshot; clean source3df4ba8; local/remote baseline matched |
| S1 contract | PASS | Golden vectors, actual C serializer vs Python, malformed/CRC/field tests; integration audit |
| S2 embedded build | PASS | firmware/build/morning-rc-build.txt and morning-rc-i2s-build.txt; real IDF exit0 |
| S3 firmware software tests | PASS | Included in full603; portable C core, real-time10s software G1 and new byte oracle; separate C7 suites |
| S4 board-absent Windows | PASS | firmware/build/morning-rc-preflight.json; host/backend/IDF READY, board NOT_DETECTED, no port opened |
| S5 host simulated integrity | PASS | Full603 includes canonical/session/fault-injection and strict no-physical-simulation acceptance |
| S6 desktop API/UI integration | PASS | Frontend tests/tsc/Vite; Rust6; API tests; source server lifecycle; packaged levels described separately below |
| S7 DSP/recording | PASS | Full603, independent extrema→float32 WAV recovery, raw retained on injected DSP failure, concurrent STOP, performance7.7x |
| S8 ML isolation | PASS | Full PyTorch regression and clean no-torch32 selected tests; explicit unavailable inference503 while USB connects |
| H0 physical identity | NOT_EXECUTED | Actual board photographs/module/connector/ROM review required |
| H1 flash/boot | NOT_EXECUTED | Operator confirmation + flash and UART/PSRAM evidence required |
| H2 real HELLO | NOT_EXECUTED | Selected actual application CDC required |
| H3 real G1 | NOT_EXECUTED | Full480000 /1875, all gates and final STOP_ACK required |
| H4 INMP441 | NOT_EXECUTED | Electrical/clock/slot checks and genuine source0 recordings required |
| H5 acoustics | NOT_EXECUTED | Controlled reference/coupling/uncertainty and physical phantom required |

Machine-readable reusable gates: [MORNING_ACCEPTANCE_MATRIX.json](MORNING_ACCEPTANCE_MATRIX.json).
Counts/hashes: [MORNING_VERIFICATION_SUMMARY.json](MORNING_VERIFICATION_SUMMARY.json).
Hardware statuses cannot be populated from software gates.

## Test results and reproducibility

Final full command at3df4ba8:

```powershell
.\.venv\Scripts\python.exe -m pytest software/tests firmware/tests tools/protocol_lab/python/test_canonical_protocol.py tools/protocol_lab/python/test_physical_acceptance_gates.py -q --junitxml=firmware/build/morning-rc-tests.xml
```

**603 passed,0 failed,0 skipped**,69.33s. Warnings: existing Starlette/httpx
deprecation and TorchScript deprecation; no weakened thresholds or fake physical test.
Separate C core executable: **7 groups passed**, strict C11 warnings/errors,
including500000-sample SPSC stress. Rust `cargo test --locked`: **6 passed**.
Frontend project tests (tsx, not a claimed Vitest run), `npm run lint` and
`npm run build`: PASS. Vite still warns about a >500kB chunk; no cosmetic rewrite.

Performance: unchanged phase-continuous100Hz/48kHz test processed240128 samples
in0.648s,370718 samples/s,**7.7x nominal real time**, versus unchanged >2x gate.
This is host software throughput, not measured USB/MCU/acoustic performance.

Clean venv installed requirements + editable package from scratch, Python3.11.9,
without torch. Selected USB/desktop/new release/missing-torch tests: **32 passed**.
An exploratory run of the entire ML test file in that no-torch environment had
**25 passed/3 failed**: corrupt-artifact status assumes torch status precedence,
positive real inference expects200, mixed-subject API expects400 before model
availability. Actual API truthfully returns dependency-unavailable503. These tests
were not relaxed or deleted. Their original PyTorch environment passes in603;
the no-torch hardware contract is independently tested. This portability caveat
remains documented rather than falsely claiming universal ML test success.

The clean environment proves core installation on this Windows host; it does
not prove another laptop has Python, SDK, drivers, MSVC, WebView2 or a data cable.
Use the checked-in laptop guide and passive checker there.

## Firmware and flash readiness

Both current configurations compiled using ESP-IDF5.5.1 / Xtensa GCC14.2.0
esp-14.2.0_20241119, managed esp_tinyusb2.2.0/tinyusb0.19.0~3. G1 app268112 bytes;
I2S compile-check app294880 bytes. Factory partition3MiB at0x10000,
partitions0x8000, bootloader0;16MB DIO80 flash, octal8MB/80 PSRAM configured only.

G1 app SHA256:
`9ebe95852d92959bf581fbe7fe6da7df8dc3bc745075428e8f57a3726a5ce0b1`.
I2S compile-check SHA256:
`d18e03d1ce39b347ae167fd506a27527b2f7f7721e3b28829f43b34fe30cc3f2`.
Neither binary establishes physical boot. Exact config/lock/all binary
hashes are in the compact summary and the local generated build manifest.

Local preserved release: `firmware/build/releases/3df4ba8-morning-g1/`;
current CLI default: `firmware/build/release/firmware_build_manifest.json`.
No transient build products are committed. Security-enabling configurations and
non-UART debug routing are rejected; manifest sdkconfig and binary hashes must
match immediately before an explicitly confirmed flash. Older manifests missing
the preserved config must be rebuilt with this CLI. No automatic flashing.

## Desktop delivery levels

Developer mode: clean install, actual source backend HTTP lifecycle, API/recording
integration and frontend build tested. Exact two-terminal start is in
[WINDOWS_LAPTOP_SETUP](../hardware/WINDOWS_LAPTOP_SETUP.md#uygulamayı-aç).
No global Python or special workstation path is required.

Packaged mode: actual PyInstaller Windows backend and NSIS installer builds were
performed from host source9788d74 (unchanged by the subsequent firmware-only fix).
Backend executable HTTP smoke checks health, serial enumeration, disconnected state,
optional model listing, a deliberately short simulated recording and failed-G1 ZIP export.
The short simulated run is expected to fail full G1; no physical port is opened. The packaged Tauri application was also started with a hidden startup window: its
Rust manager resolved bundled resources, verified backend HTTP health and released
the child listener after application close. This is startup/cleanup smoke, not
interactive visual QA. Final artifact hashes and execution
levels are recorded in the verification summary. Installer **installation** and
interactive WebView/Device Center operation remain NOT_EXECUTED. Compilation is
not a claim of an installed user workflow. Packaged tools do not contain ESP-IDF
or the repo CLI; use the source checkout for flashing. No drivers/system settings
were installed by this operation.

## Remaining issues and assumptions

No known unresolved software P0 or first-contact P1 after fixes and regression.
Physical inspection is a blocking prerequisite to hardware writes and wiring.
P2: RAM-buffered recorder persists WAV only on STOP; crash/power loss can lose
unfinalized audio, so use short sessions and retain incomplete markers. This RC
does not claim crash-proof acquisition. P2: positive ML test portability caveat
above; optional dependency absence is tested and does not block USB. P2: existing
frontend chunk and deprecation/linker warnings. Physical MCU heap/stack/USB clock,
PSRAM, missing-mic signal behavior, pins and acoustic fidelity remain unmeasured.

Receipt/counts of ordered electronics are not confirmed. Chestpiece and silicone/
gel coupling parts are not purchased. Lehim/header/tool availability must be
checked; PAM8403/exciter and AUX cable cutting are outside first G1/G2 wiring.
Frozen MurmurMIL/data/checkpoints/metrics remain unchanged; no hardware-domain
inference validation or clinical claim.

## Exact next actions

1. Open `docs/engineering/hardware/START_HERE_TOMORROW.md` in the repo on the laptop.
2. Run `.\.venv\Scripts\python.exe tools/hardware/bringup.py doctor`; follow setup if missing.
3. Photograph/inspect actual board, select one connector and record Windows IDs.
4. In exported IDF5.5.1 shell build; explicitly identify/confirm flash on the selected ROM COM.
5. Capture reviewed UART boot; passive watch for new COM; HELLO on actual native CDC.
6. Run physical-only g1 or Device Center source1 with the other reader disconnected.
7. Preserve `experiments/hardware/<UTC_unique>/` or Desktop ZIP even on failure;
   send terminal output, Device Manager/PCB pictures and logs for troubleshooting.
8. Only after physical G1 and electrical checklist, enable reviewed source0, build/
   confirm flash, record quiet/control raw sessions and run `qualify`. No acoustic
   acceptance from speech/claps alone.
