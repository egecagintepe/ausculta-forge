# W05 Module C: Live Display and Recording Verification

**Week:** 5
**Module:** C — Computer Application & Quality Assessment
**Owner:** Ege Çağın Tepe
**Status:** PARTIAL CLOSEOUT — CLI G1 PASS (106d3e0); GUI G1 PASS (59d773e); FINAL e90785e G1 REPEAT NOT_EXECUTED; G2 PENDING
**Reconciled:** 2026-10-26 against `106d3e0`; not a physical test date.

## Objective

Reconcile host verification and the reported physical ESP32-S3 USB G1 CLI result without treating synthetic acquisition as microphone acceptance or accepting the new GUI by inference.

## Work Performed and Existing Evidence

- Historical [host preflight](W05_C_host-integration-preflight_v01.md) records 34 device-runtime and 281 repository tests passing at its original baseline, including normalization, ordering, interruption and WAV/JSON integrity. These are historical software results, not tests run today.
- Historical [virtual bench](W05_C_virtual-bench-verification_v01.md) records deterministic pipeline verification tagged `SOFTWARE_KNOWN_ANSWER`; it cannot establish a physical pass.
- [Morning release report](../../../../engineering/release/MORNING_RELEASE_REPORT.md) and [summary](../../../../engineering/release/MORNING_VERIFICATION_SUMMARY.json) record 603 Python tests, 7 C groups, 6 Rust tests and frontend checks at `3df4ba8`, with physical gates then `NOT_EXECUTED`. These historical results do not validate `106d3e0` or a later physical run.
- Source at `106d3e0` includes canonical USB host/acceptance code in `software/pcg_app/canonical/`; recent engineering commits address diagnostics, filter/G1 controls and desktop acquisition lifecycle. Implementation does not establish joint academic approval or physical GUI acceptance.
- The user confirmed a successful physical ESP32-S3 USB G1 CLI trial in the 2026-10-26 reconciliation request. The actual trial date, board identity, firmware/host revisions and numeric outputs were not supplied here.

## Current Acceptance Boundary

| Item | Status | Limit |
|---|---|---|
| Physical USB G1 through CLI | PASS — NEW MINI PC RUN | 2026-10-26 07:50 UTC; host `106d3e0`, COM7 / `303A:4001`, firmware 1.1.0, protocol 1.0. Evidence `experiments/hardware/week6_20261026_sprint/cli-g1/20261026T075048Z_f26df565`. |
| New GUI physical G1 / automatic STOP / export | PASS at 59d773e; final e90785e full rerun NOT_EXECUTED | Actual Windows GUI start and ZIP export, 480000 samples / 1875 frames, zero integrity errors and STOP_ACK; no recording started. Final GUI HELLO/READY/disconnect passed after the state-message fix. |
| Real microphone G2 | PENDING | Synthetic G1 does not validate microphone wiring, real I2S input, DMA alignment or acoustic response. |
| Full `C-W05-01..09` bench matrix | PENDING ITEM-LEVEL EVIDENCE | Reported G1 success does not prove cable-pull, injected faults, sustained operation or every display/recording case. |
| Module A/B closeout | PENDING OWNER REVIEW | No owner measurement or completed submission is asserted by this reconciliation. |

## New Physical CLI G1 Evidence — 2026-10-26

Command: `.\.venv\Scripts\python.exe -B tools/hardware/bringup.py g1 --port COM7 --output experiments/hardware/week6_20261026_sprint/cli-g1`.

Actual first-attempt result: **PHYSICAL_G1_PASSED**, `is_simulated=false`, physical CDC transport, 48000 Hz, 256 samples/frame, 480000 accepted samples and 1875 frames; all acceptance gates PASS. CRC, sequence, index, timestamp, sample-value and firmware drop counters are zero. Final STOP_ACK telemetry reports generated=fully_queued=480000, frames=1875, error_code=0. COM7 exclusive-access checks passed before and after; exit code 0, stderr empty.

Original acceptance: `experiments/hardware/week6_20261026_sprint/cli-g1/20261026T075048Z_f26df565/g1_protocol_summary.json`; related sample integrity, telemetry, timing and file SHA-256 manifest are in the same directory. Command/UTC/host/exit/release record: `experiments/hardware/week6_20261026_sprint/cli-run.json`, stdout/stderr alongside it. Expected sample-sequence hash and observed accepted-sample hash match: `08f55010ada204d8f4631749b2976afd432a29167c3a8a2220a46fad6386ce96`.

The local `3df4ba8` firmware build manifest passed config/artifact hash validation and reports 1.1.0. This does **not authenticate the image flashed on the board**; HELLO identifies reported compatibility only. No flash/reset was performed. No WAV recording was started during this physical run, so no physical WAV/JSON recording result is claimed.

Earlier 14 diagnostics ZIPs still contain NOT_EXECUTED; they are unchanged historical evidence, not the provenance of this new run. Earlier laptop-run originals are still unavailable; that does not invalidate the new independently archived mini PC result.

## Remaining Evidence and Scope Limits

- Earlier laptop-run originals remain unavailable. Do not backfill their date/device/revisions from this mini PC result.
- Actual GUI G1/export at 59d773e is archived as gui-export-evidence.zip. A header state discrepancy was fixed and tested at e90785e; final full G1 rerun remains NOT_EXECUTED under the two-start limit. See the [sprint report](../../../../engineering/release/WEEK6_SPRINT_REPORT.md) for artifact hashes and exact scope.
- Full C-W05-01..09, long-duration/cable-pull/error-injection hardware cases, G2 microphone and acoustic characterisation still require their own evidence.
- Recording integrity is verified independently with explicitly software-only tests; the physical CLI run did not create WAV/session.json artifacts.

## Open Decisions / Risks

The v01 protocol proposals remain historical. Canonical implementation does not record Ozan's approval of DW03-09/10/12 or verify physical microphone alignment. Owner sign-off remains pending unless separately evidenced.

## Next Week Handoff

Retain the newly archived CLI G1 evidence and historical outputs unchanged. Continue with the [Week-6 Module C plan](../../../week-06/submissions/module-c-ege/W06_C_spectrogram-recording-metadata.md), using software fixtures/replay first. Final e90785e full G1 repeat and real microphone G2 remain separate open gates; the 59d773e GUI result is not substituted for a final-artifact rerun. See the separate dated sprint report for subsequent software tests and application changes; no firmware write or electrical intervention was performed.
