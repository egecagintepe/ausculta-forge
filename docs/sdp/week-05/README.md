# EEE495 — Week 5 — First Hardware Bench and Synthetic Tests

**Reconciled:** 2026-10-26 against `main` at `106d3e0`. This is a documentation review date, not a test execution date. No tests were rerun for this update.
**Overall status:** PARTIAL CLOSEOUT.

| Submission folder | Owner | Current boundary |
|---|---|---|
| submissions/module-a-kaan/ | Kaan — Module A | Owner closeout pending; no measurement or completion is asserted here. |
| submissions/module-b-ozan/ | Ozan — Module B | Owner submission unchanged; historical G1 plan predates the user report below. |
| submissions/module-c-ege/ | Ege — Module C | Historical software verification exists; new CLI G1 and GUI G1 evidence archived with exact source revisions; final-artifact G1 rerun separately pending. |

## Current evidence status

- **Physical ESP32-S3 Native USB G1 CLI: PASS**, independently verified in a new mini PC run on 2026-10-26 at 07:50 UTC using host `106d3e0`, firmware `1.1.0` / protocol `1.0`, COM7 / `303A:4001`. Actual result: 480000 samples, 1875 frames, zero integrity/drop errors, STOP_ACK and port release. Original archive: `experiments/hardware/week6_20261026_sprint/cli-g1/20261026T075048Z_f26df565`. The earlier laptop run is still user-reported and is not the provenance of this new result.
- **New GUI physical G1: PASS at `59d773e`**, independently executed 2026-10-26 08:14 UTC through actual Windows UI, automatic STOP and GUI export. Final `e90785e` state-message fix was rebuilt and GUI HELLO/READY/disconnect passed; full G1 was not repeated after that fix because the two-start limit was exhausted. See [sprint report](../../engineering/release/WEEK6_SPRINT_REPORT.md).
- **Real microphone G2 and acoustic characterisation: PENDING.** Synthetic G1 does not prove microphone input, gain/bandwidth or phantom performance.
- Full Week-5 bench-case closure and Module A/B completion are not inferred from a CLI G1 pass.

See the [Module C evidence and missing-artifact register](submissions/module-c-ege/W05_C_live-display-recording-verification.md) and [decision register](decisions.md).

## Historical plan and prerequisites

- [Module B G1 bring-up plan](submissions/module-b-ozan/W05_B_g1-bringup-plan_v01.md): historical pre-test plan; its current-status limitation is superseded by the new physical CLI evidence above. The owner's file is unchanged.
- Week-4 [embedded requirements](../week-04/submissions/module-b-ozan/W04_B_embedded-requirements-freeze.md), [protocol proposal](../week-04/submissions/module-b-ozan/W04_B_to_C_protocol-proposal_v01.md) and [procurement closeout](../week-04/procurement-closeout.md) remain reference inputs, not new measurement evidence.

Do not fabricate measurements. A software build/simulator cannot prove physical G1. Archive the original run's identity, commands and logs without replacing historical evidence.
