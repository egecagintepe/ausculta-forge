# EEE495 — Week 5 Decisions

Reconciled 2026-10-26 against `106d3e0`. Evidence records and pending drafts below do not constitute retroactive team approval or test execution.

| ID | Decision Topic | Status | Owner / reviewer | Resolution / Notes |
|---|---|---|---|---|
| DW05-01 | Physical G1 CLI archival closeout | CLOSED — NEW PHYSICAL CLI EVIDENCE | Ege; original-run operator | New mini PC CLI run on 2026-10-26 07:50 UTC at host `106d3e0` passed: 480000 samples / 1875 frames, zero errors, STOP_ACK and port released. Original JSON/log/hash archive linked below; earlier laptop evidence is still user-reported. [Register](submissions/module-c-ege/W05_C_live-display-recording-verification.md). |
| DW05-02 | Separate CLI, new GUI and microphone acceptance | RECORDED — USER-CONFIRMED SCOPE | Ege | CLI G1 and actual GUI G1 have separate original evidence (106d3e0 / 59d773e). Final e90785e GUI HELLO passed; full G1 repeat NOT_EXECUTED under the two-start limit. G2 remains PENDING; no Module A/B completion is inferred. |
| DW05-03 | Historical protocol proposal vs canonical implementation | PENDING — JOINT REVIEW | Ege / Ozan | Canonical host code exists at `106d3e0`. v01 proposals are historical; formal DW03-09/10/12 owner approval is not inferred from implementation. [Review](submissions/module-c-ege/W05_C_protocol-readiness-review_v01.md). |

Historical software counts retain their original baseline. Do not substitute simulator evidence, target counts or old NOT_EXECUTED bundles for original physical-run evidence.
