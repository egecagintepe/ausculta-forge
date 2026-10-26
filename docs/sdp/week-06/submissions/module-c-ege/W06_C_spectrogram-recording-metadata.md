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
