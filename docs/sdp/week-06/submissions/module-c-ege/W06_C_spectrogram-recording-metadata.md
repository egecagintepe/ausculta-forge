# W06 Module C: Spectrogram and Recording Metadata

**Week:** 6
**Module:** C
**Owner:** Ege Çağın Tepe
**Status:** SOFTWARE VERIFICATION PASS — PHYSICAL GUI ACCEPTANCE TRACKED SEPARATELY; G2 PENDING
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
