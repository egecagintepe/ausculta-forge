# EEE495 — Week 6 Decisions

Drafted 2026-10-26 against `106d3e0`. Software criteria were executed on 2026-10-26; no Module A/B approval or G2 pass is implied. See the [Module C results](submissions/module-c-ege/W06_C_spectrogram-recording-metadata.md).

| ID | Decision Topic | Status | Owner / reviewer | Resolution / Notes |
|---|---|---|---|---|
| DW06-01 | Spectrogram window timestamp convention and gap handling | CLOSED — SOFTWARE EVIDENCE | Ege | Welch input-window start/end use acquisition seconds; direct sample-index/fs oracle passes at 4/48 kHz. UI delivery does not define the time axis; gaps reset spectral input. |
| DW06-02 | Session/source history isolation | CLOSED — SOFTWARE EVIDENCE | Ege | Stream identities and source/rate reset isolate history; bounded/rewind/reset regressions passed at 574b52e. |
| DW06-03 | WAV/JSON/hash/provenance acceptance | CLOSED — SOFTWARE EVIDENCE | Ege | Software-only WAV/JSON/hash/origin/replay and existing interruption/error tests passed; see the [Module C plan](submissions/module-c-ege/W06_C_spectrogram-recording-metadata.md). |
| DW06-04 | New GUI physical acceptance and G2 | PARTIAL — GUI G1 PASS AT 59d773e; G2 PENDING | Ege; Ozan/Kaan for their own evidence | Actual GUI G1/export passed at 59d773e. Final e90785e HELLO/READY/disconnect passed; full G1 repeat NOT_EXECUTED (two-start limit). See the [release report](../../engineering/release/WEEK6_SPRINT_REPORT.md). G2 and Module A/B tasks remain open. |

Close a decision only when the relevant review or execution evidence is linked. All proposed criteria and outputs are defined in the Module C plan.
