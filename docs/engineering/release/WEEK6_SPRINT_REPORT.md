# AuscultaForge Week-5 closeout / Week-6 Module C sprint — 2026-10-26

## Status and scope

| Gate | Actual status |
|---|---|
| Environment/source preservation | PASS — main started at 106d3e0; original 12 academic changes preserved in initial-academic.diff before reconciliation |
| Physical CLI G1 | PASS — first physical start, host 106d3e0, 2026-10-26 07:50 UTC |
| Physical Tauri GUI G1 and GUI export | PASS — second physical start, application source 59d773e, 2026-10-26 08:14 UTC |
| Spectrogram and recording software | PASS — 615 Python tests; frontend tests/typecheck/build and 6 Rust tests |
| New backend / final NSIS package | PASS — source rebuilt; embedded backend code matches source |
| Final e90785e GUI HELLO/READY/disconnect/cleanup | PASS — 2026-10-26 08:23–08:26 UTC, no START |
| Final e90785e full physical GUI G1 repeat | NOT_EXECUTED — two-start limit exhausted; the complete G1 evidence is for 59d773e, before the one-line device-event decoding fix |
| Installer installation / installed-version acceptance | NOT_EXECUTED — existing installation preserved; new release executable tested using isolated APPDATA/LOCALAPPDATA |
| Physical microphone G2 / acoustics / Module A/B measurement closure | PENDING / NOT_EXECUTED |

Machine-readable counts, commands, UTC execution bounds, artifact hashes and original-evidence hashes: [verification summary](WEEK6_VERIFICATION_SUMMARY.json). Private originals remain under `experiments/hardware/week6_20261026_sprint/`; binaries, raw identifiers and authentication-bearing runtime logs are not committed.

## Physical CLI G1

Command from repository root: `.\.venv\Scripts\python.exe -B tools/hardware/bringup.py g1 --port COM7 --output experiments/hardware/week6_20261026_sprint/cli-g1`.

COM7 / VID:PID 303A:4001 (MI_00), firmware 1.1.0, protocol 1.0, 48000 Hz and 256 samples/frame were verified. USB serial and UID are omitted here. Actual accepted samples **480000**, AUDIO frames **1875**, zero sample/index/CRC/sequence/timestamp/parser/ingestion errors, zero firmware dropped samples. HELLO, START_ACK, strict deterministic sample comparison and final STOP_ACK/telemetry passed. Result **PHYSICAL_G1_PASSED**, is_simulated=false. Exit 0, stderr empty; exclusive Windows port access passed before/after.

Original acceptance: `experiments/hardware/week6_20261026_sprint/cli-g1/20261026T075048Z_f26df565/g1_protocol_summary.json`. Its telemetry, sample/timing summaries and SHA-256 manifest are alongside it. The compiled 3df4ba8 local manifest passed config/binary hash validation, but association with the flashed image is not authenticated; HELLO version compatibility is the evidence boundary. No flash/reset or electrical operation occurred. Host/device clock calibration is not inferred from deterministic timestamps.

## Real GUI G1, export and discovered status bug

The newly built release executable at 59d773e was launched with the newly rebuilt backend in isolated test storage. Actual Windows UI interaction via Computer Use: Sensor Hardware → COM7 → Connect & HELLO → Deterministic Mode 1 → Start Acquisition. STREAMING was observed with live counters (332032 samples / 1297 frames); automatic STOP reached COMPLETE with **480000 / 1875**, all G1 gates PASS and **PHYSICAL_G1_PASSED**. The UI did not white-screen.

Export auditable G1 evidence was clicked in the GUI; the downloaded ZIP was copied without altering the original to `experiments/hardware/week6_20261026_sprint/gui-export-evidence.zip`. ZIP SHA-256: `028b137084b14791735c9edf5a0de340700000b92c24e24a1048aca8006046f5`. Every member matches its embedded SHA-256 manifest. REST GETs archived the result after the UI run; no REST connect/start/stop/export was used to substitute for GUI actions.

The GUI transport wrote 160 bytes: exactly the production serializer's HELLO 48 + START 60 + STOP 52 bytes, consistent with a single STOP. STOP_ACK and all final telemetry passed. After GUI Disconnect, exclusive COM7 access passed. Native Windows close shut down the app/backend.

A real UI discrepancy was found: device WebSocket messages flatten a string state, while the client treated that string as a nested state object. The header/footer could say NO DEVICE despite correct canonical G1 state. Fixed at **e90785e** with a production-dispatch regression covering flat and nested messages. Frontend tests/typecheck passed and NSIS was rebuilt. Final e90785e GUI HELLO showed DEVICE READY in both header/footer, zero samples, followed by disconnect and normal close; COM7 was free. Full G1 was not repeated after this display-state-only fix because both authorised physical starts were already used. This distinction is retained instead of claiming a full final-artifact physical rerun.

## Spectrogram engineering

Implementation 574b52e adds stream IDs, acquisition-window timestamps, sample rate, actual Welch nperseg/bin spacing and PSD reference to display spectra. Rate changes, gaps and replay rewind reset the spectral input. An oversized block cannot exceed the 4096/8192-sample recent buffer. The frontend retains at most 80 spectra over 15 seconds, positions columns from actual window times, rejects duplicate timestamps and isolates new sessions/sources/rates. Missing UI updates are not redistributed into continuous time.

Frequency display is min(2000 Hz, Nyquist). The default 48 kHz nperseg=1024 gives Δf=46.875 Hz; 4 kHz nperseg=256 gives Δf=15.625 Hz. Early windows report their actual parameters. Intensity is dB relative to 1 FS²/Hz; no calibrated sound-pressure/dBFS claim. Physical deterministic G1, synthetic/simulated, replay and unqualified I2S origins are distinct. Stopped display frames cannot reactivate playback status. Simulation status correction is at 59d773e.

Single/two-tone 4/48 kHz numerical tests compare timing to sample-index/fs and PSD to direct SciPy Welch; tests cover rate/gap/reset/rewind, long sessions and oversized blocks. Frontend tests exercise production history helpers, time gaps, 10000 updates, bounds, Nyquist and lifecycle labels. This is bounded Welch PSD history, not a claim of uninterrupted STFT frames or independently measured hardware clock accuracy.

## WAV and metadata

Existing and new software tests verify mono float32 WAV rate/count/values, N/fs duration, UTC ordering, sequence/timestamp limits, JSON agreement, SHA-256, tamper/corruption handling, interruption/finalisation failures and replay. Processing provenance distinguishes simulated, physical deterministic and unqualified I2S modes. Replay metadata links the original session, source/acquisition mode, WAV hash and processing profile.

Both physical G1 runs left recording OFF. **No physical raw.wav/session.json artifact is claimed.** Recording acceptance is explicitly software-only. Normalized float32 WAV is not an unchanged USB integer-byte archive. RAM buffering still permits loss of unfinalised audio on process/power failure.

## Tests, failures and warnings

Current command/exit/date records are in the summary JSON. Full Python command: `.\.venv\Scripts\python.exe -B -m pytest software/tests firmware/tests tools/protocol_lab/python/test_canonical_protocol.py tools/protocol_lab/python/test_physical_acceptance_gates.py -q --junitxml=experiments/hardware/week6_20261026_sprint/python-full.xml`: **615 passed, 0 failed**, exit 0. `npm.cmd run lint`, `npm.cmd test` (5 tsx programs), `npm.cmd run build`, `cargo test --locked` (6 passed), PyInstaller and `npm.cmd run tauri -- build --bundles nsis` all passed.

Initial targeted Python run: 46 passed / 2 failed due to an incomplete new test fixture; fixed before the full run. Initial npm test command passed but its logging wrapper failed printing Unicode under cp1254; original output/exit metadata retained, UTF-8 logging fixed, final tests passed. The GUI header bug above was observed, diagnosed and regression-tested. No physical G1 retry or third START was hidden.

Warnings are non-fatal: existing Starlette/httpx and TorchScript deprecations, Vite >500 kB chunk, Rust linker informational output, PyInstaller optional tensorboard/CUDA/cross-platform imports. Packaged backend HTTP health, passive port enumeration and disconnected session smoke passed; this does not qualify every optional ML/GPU path.

## Final Windows artifacts and provenance

Final NSIS source **e90785e**; version remains 0.1.0-alpha.1, so identify artifacts by hashes rather than filename/version alone.

- Installer: `software/frontend/src-tauri/target/release/bundle/nsis/AuscultaForge_0.1.0-alpha.1_x64-setup.exe`.
- Size: **165101259 bytes**; mtime UTC `2026-10-26T08:23:07.943719+00:00`.
- SHA-256: `dff76ce9e086a5d7435885c574fbcb3668a3dd2bdcc5e1ac872d3e0abc7a1bf9`.
- Backend executable: **58488864 bytes**, SHA-256 `0d852f9e68ab2c44b64acbef476db09d14c55c6b53a712577cb105e0ce612cb1`. Backend sources equal 574b52e; later commits change frontend only. PyInstaller was run clean after the old bundle was moved to a preserved archive. Extracted bundled Python code for pcg_app.state/display_pipeline matches current source, and Tauri's copied backend hash matches the rebuilt executable.
- Physical-G1-tested 59d773e installer preserved as `experiments/hardware/week6_20261026_sprint/gui-tested-59d773e-setup.exe`; SHA-256 `29aabaea1c4a661ced1f837e64e960f08a00b0bef4057b94efedf0109f5cd920`.

Installation was intentionally not run over the existing same-version installation. New release binaries were launched with isolated test data. User application data and previous build evidence are preserved.

## Academic closeout, Git and remaining work

The original 12 academic files are reconciled. Four v01 report bodies and old test outputs are unchanged; dated addenda describe current evidence. Week 5 is partial overall: CLI and the separately identified GUI G1 are supported, but full long-run/fault/cable-pull cases and Module A/B owner measurements remain open. Week 6 Module C has software acceptance evidence and explicitly scoped GUI evidence. Kaan/Ozan submissions are untouched.

Code commits: 574b52e (timing/provenance), 59d773e (simulation labels), e90785e (device state decoding). The following documentation commit contains this report; resolve its identity with `git log -1 -- docs/engineering/release/WEEK6_SPRINT_REPORT.md`. Normal origin/main push and equality are verified in the user handoff, without force-push.

Remaining: final e90785e full physical G1 rerun under a new authorised test budget; installer installation acceptance; actual G2 electrical/profile/real-input qualification; transducer low-frequency response, gain/noise and controlled phantom/coupling measurements. No G2, acoustic or clinical success is claimed. The decorative in-app close button is a pre-existing no-op; native Windows close was used and cleanup verified. Explicit user disconnect is also logged by the legacy journal as DEVICE_ERROR while ending in absent; it is not a G1 integrity failure.
