# W06 Module C: Spectrogram and Recording Metadata

**Week:** 6
**Module:** C
**Owner:** Ege Çağın Tepe
**Status:** SOFTWARE VERIFICATION & UX STABILIZATION PASS — AUTOMATED WINDOWS AUDIO ACCEPTANCE PASS; ACOUSTIC HUMAN HEARING ACCEPTANCE PENDING; TEAM G2 PENDING
**Plan date:** 2026-10-26
**Starting baseline:** `106d3e0`; software implementation `574b52e`, followed by simulation-status correction `59d773e` and flat device-message decoding fix `e90785e`. Original plan retained below, followed by actual 2026-10-26 execution results.

## Objective

Verify sample-timed spectrogram history and recording integrity with explicit session provenance. Complete software verification on the mini PC using deterministic inputs/replay; accept the new GUI on real USB separately. Do not promote synthetic G1 into real microphone G2.

## Starting Inputs / Dependencies (106d3e0, before this sprint)

- [Week-5 closeout](../../../week-05/submissions/module-c-ege/W05_C_live-display-recording-verification.md): new physical ESP32-S3 USB CLI G1 PASS on 2026-10-26 at 07:50 UTC is independently archived; earlier laptop evidence is still user-reported. CLI G1 does not establish physical GUI or microphone acceptance.
- `software/frontend/src/components/LiveWorkspace.tsx`: waterfall retains up to 80 spectra as frequency/power arrays. History has no per-column timestamp; no explicit session-history reset was found in the reviewed component. This is a verification gap, not a measured runtime failure.
- `software/pcg_core/scientific/spectral.py`: Welch PSD foundation. `software/tests/test_scientific_spectral.py` covers tones, frequency bins, windows and resampling; `test_display_pipeline.py` covers decoupled spectral updates and recording under slow UI.
- `software/pcg_core/recording.py`: normalized float32 WAV, JSON sidecar, SHA-256, session/source, timing, stream quality and revision/environment fields. Existing coverage: `test_recording.py`, `test_morning_release.py`, `test_usb_integration_bridge.py`.
- Frontend tests cover waveform/time-axis math, UI truth and acquisition stop gating; these do not by themselves validate waterfall column timing or physical GUI operation.
- At the starting baseline new GUI physical acceptance was PENDING; subsequent run scope is recorded below. Real microphone input/characterisation depends on separately evidenced Module B/A work; their submissions are not completed by this plan.

## Planned Work Order

1. Define the spectral window start/centre timestamp convention, source sample rate, window length/hop, units and tolerances. Map actual producer timestamps/sample indices to columns; assess gaps and delayed/coalesced delivery before implementation.
2. Review and, in a separately authorised code change, implement minimum timestamp/reset corrections. Use two distinguishable synthetic sessions and delayed/gapped delivery to verify history isolation and time mapping.
3. Run targeted spectral/display/recording/USB regression tests and frontend tests/typecheck. Capture actual command, date, environment, source SHA and exit/results; do not reuse old counts as new results.
4. Verify normal STOP and interruption/restart recording artifacts independently, including hash recomputation and replay. Preserve failures and incomplete markers.
5. Perform a separate new-GUI physical USB G1 acceptance run with identified app/firmware revisions; retain evidence even on failure. No firmware change or G2 pass is authorised by this document.

## Proposed Acceptance Criteria

The table defines the original proposed criteria. Actual status and scope are recorded below; no joint Module A/B approval is inferred.

| ID | Criterion | Required check / evidence |
|---|---|---|
| C-W06-01 | Spectrogram timestamp accuracy | Each column has session-associated sample timing and a documented window start/centre convention. Compare to an independent sample-index/fs oracle using known timed tone changes. Timestamp mapping error is at most one source sample period plus documented timestamp quantisation; spectral-window smearing is evaluated separately. Delayed/coalesced UI delivery must not compress missing time or invent uniformly acquired columns. Define the tolerance before running. |
| C-W06-02 | Frequency/power semantics | Known tones map within the declared bin resolution; record fs, window/hop, FFT size, scaling and dB reference. Do not confuse PSD-relative dB with calibrated acoustic pressure or label it dBFS without the matching definition. |
| C-W06-03 | Old-session history cleared | New session, source change and reconnect/restart clear previous history before publishing new columns. A/B inputs with distinct tones cannot leave A columns in B; session identity and time origin are unambiguous. |
| C-W06-04 | WAV + JSON consistency | Decoded WAV sample count equals JSON total_samples and accepted recorded samples; header rate equals metadata rate, channels/format agree and duration equals N/fs within declared serialisation precision. Distinguish normalized float32 storage from wire format. Rejected/corrupt packets do not enter accepted audio. |
| C-W06-05 | SHA-256 and replay | Independently recompute SHA-256 over the final WAV bytes and match raw_wav_sha256; modified copies fail integrity checking. Replay preserves sample count/rate and expected values within storage precision. Never modify the original artifact for tamper testing. |
| C-W06-06 | Session provenance | Session ID, UTC boundaries, source/acquisition mode, sample timing/sequence limits, processing profile, termination reason, quality counters and actual app/host revision/environment are traceable. Hardware identity/firmware revision must come from that run's metadata or linked run manifest; unknown values stay explicitly unknown. New sessions cannot inherit old device/source identity. |
| C-W06-07 | Simulation/hardware distinction | Simulated/replay/known-answer origins remain explicit in UI, JSON and exported evidence. A simulator using a hardware-shaped transport cannot claim a physical pass; hardware mode alone is insufficient. Physical claims require the real-port run evidence. |
| C-W06-08 | STOP/interruption/error handling | Test normal STOP, disconnect, repeated sessions and storage-finalisation failure. Verify artifact consistency and truthful incomplete/failure status; a failed finalisation must not leave clean acceptance. No crash-proof recording claim is made. |
| C-W06-09 | New GUI physical acceptance | On real ESP32-S3 USB, independently verify connect/start, full deterministic G1 acceptance/final STOP_ACK, display/record/export and second-session isolation at identified revisions. Expected canonical target: 480000 samples / 1875 AUDIO frames; actual counts must come from the run. CLI user report is insufficient. G2 remains separate. |

## Evidence to Produce

- Dated test/run manifest: source SHA, environment, commands, configured tolerances, actual outcomes and linked logs; distinguish software-only from physical runs.
- Deterministic input definition, independent timing/frequency oracle and expected/observed comparison; screenshots supplement numerical evidence.
- Distinct A/B session captures showing timestamp/reset behaviour; original WAV + session.json pairs with independently recomputed hashes and integrity/replay results.
- Original physical CLI G1 archive when supplied; separate new-GUI physical acceptance report and device/firmware identity. Do not invent a WAV if the original CLI run did not record one.

## Spectrogram Implementation and Actual Verification — 2026-10-26

**PASS — SOFTWARE ONLY**, implementation `574b52e`:

- Display spectra now include a stream identity, exact acquisition window start/end in seconds, sample rate, actual Welch nperseg and bin spacing, plus PSD reference `1 FS²/Hz`. These timestamps describe the complete recent-data Welch input window, not UI arrival time or one STFT hop.
- History uses actual window position in a fixed 15-second time axis and retains at most 80 frames. Dropped display updates leave time gaps rather than redistributing columns. Rate change, replay rewind or acquisition gap resets the aggregator; session/source resets issue a new stream identity. The frontend clears history on identity/rate/source changes and discards duplicate timestamps.
- Display frequency range is `min(2000 Hz, fs/2)`; 48 kHz and 4 kHz sources both display 0–2000 Hz while retaining their actual PSD resolution. Current default nperseg is 1024 at 48 kHz (Δf 46.875 Hz) and 256 at 4 kHz (Δf 15.625 Hz); early windows may use fewer samples and report their actual value. Zero-padding is not claimed as extra resolving power.
- Labels distinguish physical deterministic G1, software simulation, unqualified physical I2S and replay. PSD intensity is relative power density, not acoustic calibration or plain dBFS. A stopped stream no longer becomes playing merely because a queued display frame arrives.
- New Python oracles cover single/two-tone inputs at both rates, window timing vs sample index/fs, direct SciPy Welch bins/power, gap/rewind/rate reset and large-block/long-session memory bounds. New frontend tests import production helpers for timestamp positions, missing updates, duplicate rejection, source/session/rate reset, 10000 updates, Nyquist and source labels; stopped/active state is tested separately.

## Recording / Metadata Actual Verification — 2026-10-26

**PASS — SOFTWARE ONLY**:

- Reused recording/integrity tests for exact sample counts, header rate, normalized float32 format, SHA-256/tamper rejection, interrupted sessions, finalisation failure and replay.
- Added software-only origin tests for simulated transport, physical-mode-1 capability model and physical-mode-0 capability model. These fixtures do not open real hardware and do not qualify G2.
- New metadata processing_profile records acquisition_origin. Replay recordings link replay_session_id and preserve the original source, acquisition mode, WAV hash and processing profile. Original files are untouched.
- New tests independently read mono float32 WAV, compare 512 samples exactly, verify 48 kHz rate, UTC ordering, first/last sequence/timestamp, N/fs duration, JSON count, byte SHA-256 and replay equality. Existing tests cover stream quality, errors, corrupted files, safety and interruption.
- The physical CLI G1 run **did not start recording**. There is no physical WAV/session.json claim from that run. `raw.wav` is normalized audio, not unchanged USB integer bytes.

## Executed Test Matrix

All current execution logs are in `experiments/hardware/week6_20261026_sprint/`; each run JSON records command, UTC bounds, working directory and actual exit code.

| Command / scope | Actual result | Evidence |
|---|---|---|
| `.\.venv\Scripts\python.exe -B -m pytest software/tests firmware/tests tools/protocol_lab/python/test_canonical_protocol.py tools/protocol_lab/python/test_physical_acceptance_gates.py -q --junitxml=experiments/hardware/week6_20261026_sprint/python-full.xml` | PASS: 615 passed, 0 failed, 2 warnings, exit 0 | python-full.txt/.json/.xml |
| `npm.cmd run lint` | PASS, exit 0 | frontend-statefix-lint.txt/.json |
| `npm.cmd test` | PASS: all 5 tsx test programs, exit 0 | frontend-statefix-test.txt/.json |
| `npm.cmd run build` | PASS, exit 0; large-chunk warning | frontend-build.txt/.json |
| `cargo test --locked` | PASS: 6 tests, exit 0 | rust-tests.txt/.json |

Initial targeted run: 46 passed / 2 failed because the new test-only capability fixture omitted get_summary; fixture corrected and full 615-test run passed. Initial npm tests themselves exited 0, but the outer logger failed printing Unicode under cp1254; its log and exit metadata were preserved, the logger was corrected to UTF-8, and the final frontend suite passed. These are recorded failures, not physical-test retries.

Warnings: existing Starlette/httpx and TorchScript deprecations; frontend >500 kB chunk warning; Rust linker informational output classified as a warning. These are distinct from failures.

## Acceptance Status

C-W06-01..08: **PASS within the software test scope above**. Physical clock calibration, visual inspection across every source, crash-proof durability and acoustic metrology are not established by these tests. C-W06-09: **GUI physical G1/export PASS at 59d773e**. A header device-state bug was fixed with a production-dispatch regression at e90785e; final GUI HELLO/READY/disconnect passed with zero samples and no START. Full e90785e G1 repeat is **NOT_EXECUTED (two-start limit)**. Exact artifact/run scope is reported in the [sprint release report](../../../../engineering/release/WEEK6_SPRINT_REPORT.md). Real microphone G2 remains PENDING.

## Open Decisions / Risks

See [Week-6 decision drafts](../../decisions.md). Window timing/reset and current software regressions are verified as described above; physical GUI evidence is tracked separately. RAM-buffered recording can lose unfinalised audio on crash/power loss; use bounded sessions and preserve incomplete status. Microphone G2, analogue gain/bandwidth and acoustic phantom performance remain open and outside Module C software-only acceptance.

## Next Week Handoff

Deliver the acceptance matrix with each criterion linked to actual evidence or a specific remaining blocker. Ege owns Module C closure; Kaan/Ozan retain ownership of their measurements and approvals. Do not mark Week 6 complete while software criteria or new-GUI physical acceptance lack evidence.


## Offline Real PCG Dataset Acceptance

Executed 2026-10-26; baseline `61cd48a`, implementation `06315de5d09f3fef915fd3ba14f84bdaada56d84`. Tests ran with then-uncommitted source changes; session HEAD alone is not clean-tree provenance. Historical software PASS and CLI/GUI G1 evidence above are preserved unchanged. No COM7/G1/G2/firmware/installer work was done in this acceptance.

**PARTIAL overall.** Bounded backend recording/spectral/replay: **PASS**. Actual browser-rendered source GUI import: **5/5 PASS**; this is not packaged Tauri acceptance. Local frontend audition and backend replay are separate paths.

| Recording | fs (Hz) | N | Duration (s) | Nyquist / final Welch Δf (Hz) | Full-file backend WAV+JSON/hash/replay |
|---|---:|---:|---:|---:|---|
| C1 / 40058_AV.wav | 4000 | 47552 | 11.888 | 2000 / 15.625 | PASS |
| C2 / 24160_MV.wav | 4000 | 90368 | 22.592 | 2000 / 15.625 | PASS |
| C3 / 49568_PV.wav | 4000 | 113792 | 28.448 | 2000 / 15.625 | PASS |
| C4 / 49627_TV.wav | 4000 | 127360 | 31.840 | 2000 / 15.625 | PASS |
| P1 / a0001.wav | 2000 | 71332 | 35.666 | 1000 / 7.8125 | PASS |

CirCor v1.0.3 supplied four officially checksum-verified WAV/HEA/TSV triplets; Challenge 2016 v1.0.0 supplied one officially verified WAV. License/access checked: Open Data Commons Attribution License v1.0. Sources, attribution, exact URLs, local manifest/hash inventory, UTC bounds, commands and outcomes are in the [new offline report](../../../../engineering/release/WEEK6_OFFLINE_REAL_PCG_REPORT.md) and [machine summary](../../../../engineering/release/WEEK6_OFFLINE_REAL_PCG_SUMMARY.json). Raw recordings/labels and screenshots stay local and are not published to Git.

Source-rate import/export bugs were corrected (device-rate resampling and fixed-4-kHz export); backend selection now reports actual 2/4 kHz, resets processing state and records source-file SHA separately from final WAV SHA. GUI clears stale imported filenames when backend replay replaces the source. Five real GUI imports show correct rate/rounded duration and waveforms; P1 play/pause/seek and all four filter controls were observed. Local audition cannot record a backend session or produce Welch history: recording is disabled and the empty spectrum explains the supported backend-replay path. Its fixed preview is not a measured preset-filter trace.

Five complete production backend runs verify source values/count/duration, mono float32 storage, JSON/UTC/session/origin/sequence/quality fields, independent final-WAV hashes, replay equality and rejection of tampered copies. Separately, actual GUI Record/Stop controls on an API-selected P1 replay produced 8192 samples at 2 kHz (4.096 s), source-offset/sample equality and hash/replay PASS; API-selected reopening rendered that session in GUI. This does not claim the file chooser starts backend acquisition.

Backend Welch timing/frequency checks passed on all five files; source N/fs bounds use one-sample lower-bound tolerance and 1e-8 s end tolerance. GUI rendered real C1/P1 spectra with 0–2000/0–1000 Hz and Δf 15.625/7.8125 Hz. Source/stream identity and existing history regressions cover source/rate/rewind reset; earlier columns are not reused as new-session evidence. PSD is relative to 1 FS²/Hz, not acoustic calibration.

Final regression: Python **562 passed, 1 intentional no-manifest skip, exit 0**; separate manifest-enabled real acceptance **7 passed, exit 0**; frontend lint, six test programs and build **exit 0**. Initial source-rate failures, floating-bound assertion and one load-sensitive CLI help timeout are preserved in new evidence; the final complete rerun passed. See report for exact times/warnings.

Separate S1/S2 research used the existing unchanged non-production model and four reconstructed held-out CirCor records; inference received no reference labels and state 0 was ignored. C1/C2/C3 produced segmentations; C4 failed heart-rate estimation and remains included with S1/S2 F1=0. No training or clinical validation claim. The report lists every success/failure and the historical-split reconstruction caveat.

Open: local audition Welch/recording support, measured browser filter response/preset consistency, EOF-loop degraded health and replay runtime/overview ID semantics, malformed-file GUI recovery, native packaged acceptance of this revision, C4 inference failure, physical G2/acoustic calibration. Bounded recording PASS does not close these gaps or Module A/B measurements.

## Integration Verification — 2026-10-26 (Module C Final Integration)

**Baseline:** `c736bbf` (synced with `origin/main`).
**Status:** **PARTIAL** (Complete Software Pipeline & DSP Verification; Packaged Installer Acceptance & Microphone G2 Pending).

### 1. Local WAV Audition vs Backend DSP Replay Bridge
- **Gap Addressed:** In earlier revisions, opening local WAV files in the browser GUI only enabled client-side WebAudio audition, bypassing the backend Welch spectrogram history, streaming pipeline, and session recording.
- **Implementation:**
  - Added backend endpoint `POST /api/stream/upload_source_wav` accepting user-selected mono PCM16/float32 WAV files via multipart upload. Source file bytes are preserved without modification into backend assets, maintaining original SHA-256 hashes, sample counts, and source sample rates (2 kHz, 4 kHz). The backend sets the active source to `realtime_wav` with exact file provenance.
  - Added `uploadAndSelectSourceWav(file: File)` in `software/frontend/src/api/bridgeClient.ts`.
  - Added an explicit user action in `LiveWorkspace.tsx`: a dedicated `[Stream via Backend DSP]` button in the specimen header and an informative notice on the waterfall canvas when in local audition mode.
  - Scientific demarcation: The UI clearly indicates whether the audio is playing in **Local File Audition** (client-side WebAudio preview without backend recording) or **Backend DSP Stream** (full Python Welch PSD waterfall, streaming telemetry, and sidecar-backed recording).

### 2. Frontend / Backend Filter Consistency & Numerical Verification
- **Gap Addressed:** Frontend WebAudio presets and backend Python DSP had mismatched passband cutoff definitions and undocumented transfer function differences.
- **Passband Alignment:**
  - `recommended`: 20 Hz – 200 Hz (Narrow auscultation band)
  - `bell`: 20 Hz – 120 Hz (Low-frequency rumble / S3-S4 gallop)
  - `diaphragm`: 100 Hz – 500 Hz (High-frequency murmurs / clicks)
  - `extended`: 20 Hz – 600 Hz (Broad phonocardiogram auscultation band)
- **Transfer Function Demarcation:**
  - Backend Python DSP uses 4th-order Butterworth bandpass filters implemented via second-order sections (SOS), yielding 24 dB/octave rolloff.
  - Frontend WebAudio uses cascaded 2nd-order Biquad highpass and lowpass filters, yielding 12 dB/octave rolloff.
- **Numerical Frequency Response Verification:**
  - Python: `software/tests/test_filter_transfer_response.py` verified single-tone attenuation and passband gain across 2 kHz and 4 kHz for all four presets (9/9 passed, exit 0).
  - Frontend TypeScript: `software/frontend/src/tests/filter_transfer_response.test.ts` verified Biquad transfer function frequency responses at 2 kHz, 4 kHz, and 48 kHz (all presets verified, exit 0).

### 3. Loop EOF Wrap & Conscious Rewind Health
- **Gap Addressed:** Continuous loop replay previously degraded stream health to `DEGRADED` upon reaching EOF due to sequence regression flags.
- **Implementation:**
  - Implemented `notify_rewind()` on `StreamQualityMonitor` and `LiveStreamingPipeline` (`software/pcg_core/streaming.py`).
  - Clears sequence/timestamp continuation pointers so the subsequent cycle starts cleanly from sequence 0 without wiping legitimate historical drop/anomaly counters or falsely resetting health to OPTIMAL.
  - Causal filter delay lines (`zi`) are cleanly reset to avoid transient discontinuities.
  - Active session recordings cleanly finalize on loop EOF wrap with `termination_reason="completed"`.
  - Regression verified by `software/tests/test_replay_eof_health.py` (5/5 passed, exit 0).

### 4. Real PCG Manifest-Driven Acceptance Rerun
- Evaluated five verified real PCG files from `data/raw/week6_real_pcg_20261026/manifest.json`:
  - CirCor C1 (`40058_AV.wav`, 4 kHz, 47,552 samples)
  - CirCor C2 (`24160_MV.wav`, 4 kHz, 90,368 samples)
  - CirCor C3 (`49568_PV.wav`, 4 kHz, 113,792 samples)
  - CirCor C4 (`49627_TV.wav`, 4 kHz, 127,360 samples)
  - Challenge 2016 P1 (`a0001.wav`, 2 kHz, 71,332 samples)
- Manifest SHA-256 hashes verified and unchanged.
- Backend acceptance test `test_real_pcg_acceptance.py`: 7/7 passed, exit 0. Rate preservation, sample counts, float32 WAV export, JSON metadata, and SHA-256 recomputation all passed.
- S1/S2 research check `experiments/output/week6_real_pcg_20261026/research_check.py` re-run: C1, C2, C3 segmented; C4 heart rate estimation failure preserved and truthfully reported (algorithm_status: `HEART_RATE_ESTIMATION_FAILED`).

### 5. Execution Matrix & Evidence
| Scope | Command | Outcome | UTC Time | Exit Code |
|---|---|---|---|---|
| Python Unit & Core Tests | `.venv\Scripts\python.exe -B -m pytest software/tests -q` | 577 passed, 1 skipped | 2026-10-26 10:46 UTC | 0 |
| Replay EOF Health Regressions | `.venv\Scripts\python.exe -B -m pytest software/tests/test_replay_eof_health.py -v` | 5 passed | 2026-10-26 10:40 UTC | 0 |
| Filter Response Regressions | `.venv\Scripts\python.exe -B -m pytest software/tests/test_filter_transfer_response.py -v` | 9 passed | 2026-10-26 10:42 UTC | 0 |
| Real PCG Acceptance Tests | `.venv\Scripts\python.exe -B -m pytest software/tests/test_real_pcg_acceptance.py -v` | 7 passed | 2026-10-26 10:46 UTC | 0 |
| S1/S2 Research Script | `.venv\Scripts\python.exe -B experiments/output/week6_real_pcg_20261026/research_check.py` | Executed, C4 failure preserved | 2026-10-26 10:47 UTC | 0 |
| Frontend Typecheck / Lint | `npm.cmd run lint` (in `software/frontend`) | 0 errors | 2026-10-26 10:46 UTC | 0 |
| Frontend Test Suites | `npm.cmd test` (7 test programs in `software/frontend`) | 7 passed | 2026-10-26 10:47 UTC | 0 |
| Frontend Production Build | `npm.cmd run build` (in `software/frontend`) | Built in 4.88s | 2026-10-26 10:47 UTC | 0 |
| Browser GUI Subagent Test | Chromium browser subagent against `127.0.0.1:3000` + `127.0.0.1:8000` | Playback, UI controls, filters, and status bar verified | 2026-10-26 11:07 UTC | 0 |
| Packaged Tauri GUI Installer | *Explicitly not executed pursuant to task constraint ("installer üretme")* | Stored sprint package stands | — | N/A |

### 6. Remaining Scope and Limits
- **Packaged Tauri Installer:** No new installer was built or tested in this sprint step; validation was performed on the browser-rendered application source.
- **Physical Hardware G2 / Calibration:** No COM7 connection, physical ESP32-S3 G1 run, or microphone G2 acoustic metrology calibration was performed.

## Final Desktop Release Candidate Verification — 2026-10-26

**Starting Baseline:** `ef0e5f1`
**Status:** **RELEASE CANDIDATE VERIFIED (PASS / PARTIAL GATE)**
- Packaged Backend DSP & Native Tauri Supervisor: **PASS**
- Browser GUI End-to-End Real PCG Streaming & Recording: **PASS**
- Native Tauri Automated OS File Dialog Driving: **BLOCKED / NOT_AUTOMATABLE** (requires human interactive desktop operation; native file dialogs not automatable via browser CDP)
- System-Wide NSIS Installation: **HELD AT ACCEPTANCE GATE** (to preserve host Windows installation without unapproved overwrite)
- Microphone Acoustic G2: **PENDING** (retained as separate Module A/B hardware work)

### 1. Hardened WAV Upload Endpoint (`POST /api/stream/upload_source_wav`)
- **Bounded Reading:** Enforces `MAX_WAV_UPLOAD_BYTES = 50 * 1024 * 1024` (50 MB) via 64 KB streaming chunk reads, returning HTTP 413 if exceeded.
- **Filename Sanitization:** Enforces `MAX_FILENAME_LENGTH = 255`, alphanumeric/underscore/dot/hyphen sanitization, and path-traversal rejection.
- **Encoding Validation:** Strict validation of mono PCM 16-bit (`np.int16`) and 32-bit floating-point (`np.float32`) formats; stereo and unsupported encodings (e.g. int32) return HTTP 400.
- **Sample Rate Validation:** Restricts rates to finite, positive medical PCG bounds: `100 Hz <= fs <= 192000 Hz`.
- **Signal Quality Sanity:** Detects and rejects NaN or Infinite values in floating-point audio.
- **Staging & Failure Cleanup:** Employs atomic staging via temporary files (`upload_tmp_...`) with automatic cleanup on error. Confirmed that failed uploads leave zero orphaned files in `assets_dir` and preserve the stream manager's active state without disruption.
- **Automated Coverage:** 12 unit/integration tests in [`software/tests/test_app.py`](file:///C:/Dev/Antigravity/bitirme/ausculta-forge/software/tests/test_app.py) all PASS (exit code 0).

### 2. Standalone Backend & Tauri NSIS Re-Packaging
- **PyInstaller Standalone Backend:** Re-bundled directly from updated Python sources via `software/build_desktop_backend.py`.
  - Executable: `software/dist_backend/auscultaforge-backend/auscultaforge-backend.exe`
  - Size: **58,493,579 bytes**
  - SHA-256: `c163e182eb6b8e59ed93285bf31c00a707da2ec2c6b72cdad72e69b6de26b38f`
- **Frontend & Rust Quality Gates:**
  - Rust process manager & IPC tests: 6 passed, 0 failed (`cargo test --locked`, exit code 0).
  - Frontend TypeScript lint: 0 errors (`npm.cmd run lint`, exit code 0).
  - Frontend test suites: 7 passed (`npm.cmd test`, exit code 0).
  - Production frontend bundle: `vite build` completed in 4.95s (exit code 0).
- **Native Tauri NSIS Release Installer:**
  - Target: Windows x64 NSIS bundle (`npm.cmd run tauri -- build --bundles nsis`).
  - Installer: `software/frontend/src-tauri/target/release/bundle/nsis/AuscultaForge_0.1.0-alpha.1_x64-setup.exe`
  - Size: **164,522,399 bytes**
  - SHA-256: `d6e0e4e3635577c1df15110166d88d2cae780f642b2b3718118b425e95f36885`
- **Native Release Executable:**
  - Path: `software/frontend/src-tauri/target/release/auscultaforge-desktop.exe`
  - Size: **9,138,688 bytes**
  - SHA-256: `a85207b0d55ea6c2e11844defffa7b93bdbc21f471aa3f4788cb0f79ef72a09b`
- **Previous Installer Preservation:**
  - The previous sprint installer is preserved at `experiments/hardware/week6_20261026_sprint/e90785e-nsis-setup.exe` (165,101,259 bytes, SHA-256 `dff76ce9e086a5d7435885c574fbcb3668a3dd2bdcc5e1ac872d3e0abc7a1bf9`).

### 3. Native Release Executable Lifecycle Verification
- Executed via [`experiments/hardware/week6_20261026_sprint/test_native_release_executable.py`](file:///C:/Dev/Antigravity/bitirme/ausculta-forge/experiments/hardware/week6_20261026_sprint/test_native_release_executable.py) with isolated test environments: `gui-rc-appdata` and `gui-rc-localappdata`.
- **Observed Behavior:**
  - `auscultaforge-desktop.exe` spawned bundled `auscultaforge-backend.exe` under Windows Job Object with parent watchdog.
  - Backend dynamically bound to ephemeral loopback port `58231` and generated a dynamic authentication token.
  - Authenticated `/api/health` returned: `{"status": "ok", "app": "AuscultaForge", "version": "0.1.0-alpha.1"}`.
  - Authenticated `/api/status` returned valid uninitialized stream state (`source_type: "none"`, `filter_preset: "recommended"`, cutoffs 20–200 Hz).
  - Uploaded CirCor C1 (`40058_AV.wav`) directly to the packaged backend server: parsed 4000 Hz, 47,552 samples, verified SHA-256 `108df8f77491a5706209aa5b467ed10ac43f2a0b847801fe666ba8146dcbf8e8`, and successfully activated live `realtime_wav` DSP stream.
  - On desktop application termination, the Windows Job Object and watchdog immediately terminated the backend process and released ephemeral port `58231`.
  - Archived in `experiments/hardware/week6_20261026_sprint/gui-rc-launch-report.json`.

### 4. Real PCG Manifest Verification
All five licensed PCG records from `data/raw/week6_real_pcg_20261026/manifest.json` re-verified:
- C1 (`40058_AV.wav`): 4000 Hz, 47,552 samples, SHA-256 `108df8f77491a5706209aa5b467ed10ac43f2a0b847801fe666ba8146dcbf8e8` — PASS
- C2 (`24160_MV.wav`): 4000 Hz, 90,368 samples, SHA-256 `fa8e0586c00bc2e86e88c9ea55853cad01a558a3c5c5945cc1ffd567545565a9` — PASS
- C3 (`49568_PV.wav`): 4000 Hz, 113,792 samples, SHA-256 `34cf7450302b1c411516e87f287e0766336a5a3064ec0e72251a24d271f28014` — PASS
- C4 (`49627_TV.wav`): 4000 Hz, 127,360 samples, SHA-256 `fa8331d27576ce81452a38a72bf30ec997a387532dc51bc0411a7f0525916382` — PASS
- P1 (`a0001.wav`): 2000 Hz, 71,332 samples, SHA-256 `c7efb3f462bbfa96dcae3c9fe343467c699fa8ce324835a643d67f70b213192e` — PASS
- Acceptance test `test_real_pcg_acceptance.py`: 7/7 passed (exit code 0).
- S1/S2 research check: C4 heart-rate estimation failure preserved (`HEART_RATE_ESTIMATION_FAILED`).

### 5. Native Windows Audio Playback & Source State Bugfix (2026-10-26)
- **Problem Diagnosis:**
  - Manual testing on native Windows x64 build with real CirCor recording (`40058_AV.wav`, 4000 Hz, 11.888s) and recorded session `session_20261026_121726_530cde89` revealed two critical issues:
    1. During backend DSP replay, waveforms animated on screen, but user heard no speaker sound, and clicking PLAY generated ~0.5s of wind/static noise before cutting off.
    2. Opening a local WAV as Local Audition appeared successful, but navigating back showed the active source was reverted to the previous session replay.
- **Root Cause:**
  - Backend streaming operates on 25 Hz decimated display points over WebSocket, not PCM speaker streaming.
  - `handleTogglePlay` mistakenly invoked `audioEngine.play()` during backend replay with a stale buffer.
  - Channel 0 was pre-filtered in software and then double-filtered through WebAudio BiquadFilterNodes in series, causing phase distortion and transient cutoff.
  - `onStreamState` events lacked an unconditional guard for local audition, allowing backend `is_streaming: true` messages to stomp over `sourceType` and active file metadata.
- **Architecture & Fixes:**
  - **Local Audition:** Dedicated WebAudio playback engine for local `.wav` files and starter models with direct speaker output and software Biquad filtering (single-pass).
  - **Backend DSP Replay:** Dedicated Python Welch waterfall, decimation, and telemetry pipeline. Marked with truthful badge: `[TELEMETRY (SPEAKER: LOCAL AUDITION)]`.
  - **Recorded Session Audition:** Added `GET /api/sessions/{session_id}/wav` endpoint in FastAPI and added **Audition** button alongside **Replay** in `SamplesView.tsx`, enabling full WebAudio speaker audition of recorded PCG sessions.
  - **State Isolation:** In `App.tsx`, `onStreamState` strictly ignores backend stream messages while in Local Audition, and switching to backend streaming explicitly clears `audioEngine`.
- **Quality Gates & Regression Tests:**
  - Added `software/frontend/src/tests/audio_playback_regression.test.ts` (8 passed).
  - All 8 frontend test suites passed (`npm.cmd test`).
  - Frontend TypeScript lint: 0 errors (`npm.cmd run lint`).
  - Frontend production build: `vite build` completed in 14.91s (`npm.cmd run build`).
  - Python tests: `test_app.py` (13 passed), `test_real_pcg_acceptance.py` (2 passed, 1 skipped), `test_morning_release.py` (24 passed).
  - Prioritized UX bug backlog catalogued in [`docs/engineering/backlog/WEEK6_UX_AUDIO_BACKLOG.md`](file:///C:/Dev/Antigravity/bitirme/ausculta-forge/docs/engineering/backlog/WEEK6_UX_AUDIO_BACKLOG.md).
- **Physical Speaker Acceptance:** PENDING until physical user acoustic listening verification.

### 6. Week 6 Audio Fix Release Build & Acceptance (2026-10-26)
- **Standalone Packaged Backend:**
  - Packaged via PyInstaller into `software/dist_backend/auscultaforge-backend/auscultaforge-backend.exe` (SHA-256: `9605b4df6966fe7a66e004cf3623f5db8f19216c8cde9d1d90f9a8b65429e7c5`, 58,493,866 bytes).
  - Verified `GET /api/sessions/{session_id}/wav` audio download endpoint, path traversal protection, and `/api/health`.
- **Production Tauri Release & Installer:**
  - Release executable: `software/frontend/src-tauri/target/release/auscultaforge-desktop.exe` (SHA-256: `99e1000bf053c6458b122ead8489f7c8fb68cc78660ca30681e6a703993fb812`, 9,139,200 bytes).
  - NSIS setup installer: `software/frontend/src-tauri/target/release/bundle/nsis/AuscultaForge_0.1.0-alpha.1_x64-setup.exe` (SHA-256: `29aac14209df7e1c82d1fe0bdd0a3c1076fa754db3a466b79e1920367e1ad2f4`, 164,521,275 bytes).
  - Built from source commit: `ccc98eb54280e10b975a757be8d58ec68689411d`.
- **Test Matrix Execution:**
  - Python test suite: 583 passed, 1 intentional placeholder skipped, 0 failed.
  - 48 kHz streaming performance suite: 6 passed (240,128 samples continuous ingestion at > 2.0x real-time speed, 0 dropped samples, 0 MCU sequence gaps).
  - Real PCG manifest acceptance suite: 7 passed with local verified manifest (`C1`, `C2`, `C3`, `C4`, `P1`).
  - Rust unit tests: 6 passed, 0 failed (`cargo test`).
  - Frontend TypeScript lint: 0 errors (`tsc --noEmit`).
  - Frontend test suites: 8 suites passed (including all 8 audio playback & synchronization regression tests).
- **Isolated Native Runtime Verification:**
  - Verified in isolated APPDATA/LOCALAPPDATA environments.
  - Dynamic ephemeral port handshake, backend supervision, `/api/health` OK.
  - Real PCG WAV upload (`40058_AV.wav`, 4000 Hz, 11.888s) preserved.
  - Session recording and `GET /api/sessions/{session_id}/wav` verified.
  - Source transitions (`realtime_wav` -> `session` -> `synthetic_dev` -> `realtime_wav`) confirmed state stomping elimination.
- **GUI Behavioral Verification:**
  - Audition button present in Recorded Sessions.
  - Replay and Audition clearly separated.
  - Local WAV does not restore old replay header.
  - 4000 Hz and actual duration correctly displayed.
  - Dynamic `L-{sampleRate}-RAW` badge displayed.
- **Physical Acoustic Gate:** PENDING user listening confirmation. Full verification report in [`docs/engineering/release/WEEK6_AUDIO_FIX_RELEASE_VERIFICATION.md`](file:///C:/Dev/Antigravity/bitirme/ausculta-forge/docs/engineering/release/WEEK6_AUDIO_FIX_RELEASE_VERIFICATION.md).

### 7. Autonomous Native Desktop Audio Acceptance (2026-10-26)
- **Execution Methodology:** Autonomous Windows UI Automation (`uiautomation` / `pywinauto`) on interactive desktop `WinSta0\Default` combined with an out-of-process WASAPI loopback audio recorder. No manual clicking or screenshots required.
- **Target Session:** `session_20261026_121726_530cde89` (CirCor `40058_AV.wav`, 4000 Hz, 27,968 samples, 6.992s).
- **Automated Native GUI Navigation:**
  - Discovered running release window `AuscultaForge — Engineering Workstation` (HWND `723314`, PID `12088`).
  - Automated tab selection to `Specimen Archives` (`nav-samples`) and tab `Recorded Sessions`.
  - Located target card `session_20261026_121726_530cde89` and triggered `Audition` (`btn-audition`).
  - Transitioned to `SPEAKER AUDITION` mode; verified 4000 Hz sample rate and exact 6.992s length.
  - Performed automated transport sequence: `PLAY` (2.5s) -> `PAUSE` (1.2s) -> `PLAY` (2.0s) -> `Seek to Start`.
- **Quantitative WASAPI Loopback Audio Measurement:**
  - Measurement device: Default Windows output `Kulaklıklar (2- Audeze Maxwell 2)`.
  - Baseline idle noise: RMS = 0.000000, Peak = 0.000000.
  - Active playback (2.5s): RMS = 0.018110, Peak = 0.153260, SNR = 125.16 dB, Active audio ratio = 37.77% (consistent with S1/S2 cardiac intervals).
  - Paused state (1.2s): RMS = 4.48e-10, Peak = 1.40e-09 (clean pause, zero buffer leak).
  - Resumed active (2.0s): RMS = 0.010518, Peak = 0.080809 (continuous playback confirmed).
  - Premature 0.5s cutoff bug: **ELIMINATED**. Continuous PCM signal verified well beyond 0.5s.
- **Replay vs Audition Demarcation & Isolation:**
  - Replay triggers backend telemetry badge: `[TELEMETRY (SPEAKER: LOCAL AUDITION)]`.
  - Switching back to Audition displays `[SPEAKER AUDITION]` and preserves original filename `session_20261026_121726_530cde89.wav` without `Session Replay: ` state stomping.
- **Multi-Source Real PCG Verification (C1–C4, P1):**
  - All 5 records verified bit-exact against SHA-256 and declared sample rates (C1–C4 @ 4000 Hz, P1 @ 2000 Hz).
  - Display aggregators, Welch frequency resolutions (Δf 7.8125 Hz vs 15.625 Hz), and source metadata strictly isolated.
- **Acceptance Status:**
  - Native GUI interaction: **PASS**
  - Local WebAudio playback: **PASS**
  - WASAPI audio output measurement: **PASS**
  - Session Audition: **PASS**
  - Backend telemetry Replay: **PASS**
  - Source state isolation: **PASS**
  - Physical human hearing acceptance: **PENDING** (until manual human listening approval).
- **Documentation & Evidence:**
  - Detailed report: [`docs/engineering/release/WEEK6_AUTONOMOUS_NATIVE_AUDIO_ACCEPTANCE.md`](file:///C:/Dev/Antigravity/bitirme/ausculta-forge/docs/engineering/release/WEEK6_AUTONOMOUS_NATIVE_AUDIO_ACCEPTANCE.md).
  - Machine summary: [`docs/engineering/release/WEEK6_AUTONOMOUS_NATIVE_AUDIO_ACCEPTANCE.json`](file:///C:/Dev/Antigravity/bitirme/ausculta-forge/docs/engineering/release/WEEK6_AUTONOMOUS_NATIVE_AUDIO_ACCEPTANCE.json).
  - Local WAV captures and JSON execution trace stored in `experiments/hardware/week6_20261026_sprint/acceptance_evidence/`.

### 8. Week 6 Final Closeout & UX Stabilization (2026-10-26)

- **UX Stabilization & Bug Fixes:**
  1. *Specimen Archives Layout Obstruction (P2):* Fixed `SamplesView.tsx` scrollable container bottom padding by expanding from `pb-8` to `pb-28` (112px). The final recorded session card is now completely visible above the fixed bottom status footer across all viewport heights.
  2. *Misleading Drive Phrasing & Click Event Separation (P3):* In `HomeView.tsx`, replaced ambiguous `Browse Workstation Drives` with an explicit HTML button labeled `Choose Local Audio File (*.wav, *.mp3)` (`id="browse-local-files-btn"`). Added `e.stopPropagation()` preventing inadvertent navigation bubbling to the reference corpus archives. Renamed the reference archive button to `Open Reference Corpus & Sessions` (`data-testid="open-samples-archive-btn"`).
  3. *Live Recording Timer Synchronization (P2):* Fixed frozen `REC 0.0s` indicator. `StreamManager` now calculates elapsed recording duration strictly as `total_samples / sample_rate_hz` and broadcasts `recording_state` updates at 5 Hz (200 ms throttle) during active recording. Pause operations freeze sample acquisition and elapsed time cleanly; stream resumption continues counting from the exact sample index.
  4. *Manifest Export Feedback (P3):* Wired `onToast` and `onLog` notification callbacks into `SamplesView.tsx`. Successfully exporting session manifests triggers an instant toast alert (`Manifest exported: manifest_<id>...json`) and an audit trail log entry; download failures display error toasts.
  5. *Version Semantics Disambiguation (P3):* Resolved architectural ambiguity between DSP backend and desktop client versions. `SessionMetadata` and manifest export JSON schema now explicitly specify `dsp_engine_version: "2.0.0"` and `desktop_client_version: "0.1.0-alpha.1"`, while maintaining backward-compatible `app_version: "2.0.0"` fallback for legacy v1.0.0 and v2.0.0 manifests.

- **Automated WASAPI Loopback Audio & SNR Clarification:**
  - Automated Windows WASAPI loopback output measurement: **PASS**. The loopback recorder confirms active PCM audio stream flow to the Windows default sound device (`Kulaklıklar (2- Audeze Maxwell 2)`), with active playback RMS = 0.018110, clean zero-buffer pause (RMS = 4.48e-10), and sustained playback eliminating the former 0.5s cut-off defect.
  - *Acoustic / Clinical SNR Interpretation Caution:* The measured digital loopback SNR of 125.16 dB is computed against a digital zero baseline (idle RMS = 0.000000). **This measurement must strictly NOT be interpreted as real acoustic, transducer, or clinical phonocardiogram SNR.** It solely proves that digital audio samples are actively dispatched to and rendered by the Windows audio engine without truncation or driver stalls.
  - *Physical Human Ear Listening:* Remains **PENDING** until verified by human auditory perception.

- **Standalone Release Packaging & Provenance:**
  - Standalone PyInstaller backend: `software/dist_backend/auscultaforge-backend/auscultaforge-backend.exe` (SHA-256: `e2407a59f3024ff886acffa09c91c6e0c4f2a2ea9103ebff366c1b895a8ff442`, 58,952,619 bytes).
  - Tauri NSIS setup installer: `software/frontend/src-tauri/target/release/bundle/nsis/AuscultaForge_0.1.0-alpha.1_x64-setup.exe` (SHA-256: `d86b3e330e9e182b2c9af46d90caed23222db5d8aa91e8b59dd404182c481943`, 165,657,128 bytes).
  - Production desktop binary: `software/frontend/src-tauri/target/release/auscultaforge-desktop.exe` (SHA-256: `8215a9e58e027275601a7e973f4078d539cbf422cfd89412d9502a1b1e3d3ce4`, 9,139,712 bytes).
  - Native release smoke test in clean environment: **PASS** (ephemeral port handshake, health checks, 4000 Hz PCG upload, clean job termination).

- **Full Test Matrix Summary:**
  - Python unit & regression tests: **587 passed**, 1 intentional placeholder skipped, 0 failed.
  - 48 kHz high-speed streaming stress test: **6 passed** (0 dropped samples, 0 packet sequence gaps at > 2.0x real-time speed).
  - Real PCG multi-session manifest acceptance: **7 passed** (`C1`, `C2`, `C3`, `C4`, `P1`).
  - Rust Tauri unit tests: **6 passed**, 0 failed.
  - Frontend TypeScript & ESLint: **0 errors**, clean compilation.
  - Frontend Vitest test suites: **9 suites passed** (including new UX stabilization regression suite).

- **Team Dependencies & Multi-Module Status:**
  - Module C (Ege Çağın Tepe): **SOFTWARE & UX PASS** — Automated audio pipeline, spectrogram rendering, session recording, manifest provenance, and desktop UX stabilized and verified.
  - Module A (Kaan): **BLOCKED / PENDING** — ESP32-S3 firmware streaming telemetry, packet flow control, and physical transducer interface awaiting completion.
  - Module B (Ozan): **BLOCKED / PENDING** — Transducer acoustic characterization, microphone calibration, and analog pre-amp validation awaiting physical lab measurements.
  - Microphone G2 Acceptance: **STRICTLY PENDING** — Synthetic and local WAV G1 verifications must not be promoted to physical microphone G2 without real acoustic measurement evidence from Modules A and B.

- **Week 7 Priority Recommendations:**
  1. *Module B Acoustic Characterization & G2 Physical Gating:* Execute physical acoustic frequency-response and SPL calibration in the lab; validate microphone transducer SNR against calibrated cardiac phantoms.
  2. *Module A Hardware Flow Control & Telemetry:* Implement MCU hardware UART flow control (RTS/CTS) and packet buffer telemetry in ESP32-S3 firmware to eliminate potential serial buffer overruns during sustained 48 kHz acquisitions.
  3. *Human Auditory Listening Protocol:* Formalize a standardized human acoustic listening evaluation protocol (ABX blind listening) for clinician review of recorded heart sound specimens.
  4. *Clinical DSP & Heart Sound Segmentation:* Advance Module C DSP algorithms with automated S1/S2 heart sound envelope extraction, murmur segmentation, and real-time clinical bandpass presets (aortic, mitral, pulmonary, tricuspid).

