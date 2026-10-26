# Module C -- Computer Application and Quality Assessment
## Submission Folder -- Week 5

| Field | Value |
|---|---|
| **Owner** | Ege |
| **Module** | C -- Computer Application and Quality Assessment |
| **Week** | 5 |
| **Purpose** | Collect all Week-5 deliverables for Module C |

## Naming Convention

All files in this folder must follow the canonical naming pattern:

`W05_C_<short-description>_vNN.<ext>`

**Examples:**
- `W05_C_example-task_v01.pdf`
- `W05_C_example-task_v01.md`

## Instructions

- Original PDF, DOCX, and XLSX deliverables may be placed in this folder alongside Markdown summaries.
- **Do not fabricate measurements, results, or component decisions.** Record only what has actually been performed.
- **Preserve original source files** when uploading (do not replace earlier versions; increment the version suffix instead).
- Where possible, commit evidence files from your own GitHub account so the contribution history reflects your individual work.

## Status

As reconciled on **2026-10-26**: historical host preflight is complete; a **new physical CLI G1 PASS** was verified on the mini PC at host `106d3e0`. The [closeout register](W05_C_live-display-recording-verification.md) links original evidence. Earlier laptop evidence is still unavailable. **GUI G1 PASS at 59d773e** has its own physical run/export evidence. Final e90785e GUI HELLO/READY passed; its full G1 repeat was not executed due to the two-start limit. **G2 remains PENDING.** Historical test outputs were not rerun as part of the earlier documentation update; current sprint executions have their own dated logs.

### Deliverables in this Folder:

| Deliverable File | Description | Status |
|---|---|---|
| [`W05_C_host-integration-preflight_v01.md`](W05_C_host-integration-preflight_v01.md) | Host integration preflight test report and C-W05-01..09 acceptance mapping | Complete (`SOFTWARE_KNOWN_ANSWER` verified) |
| [`W05_C_protocol-readiness-review_v01.md`](W05_C_protocol-readiness-review_v01.md) | Joint B→C wire protocol review, CDC-ACM vs Bulk analysis, and INMP441 reconciliation | Complete (Awaiting Module B sign-off) |
| [`W05_C_live-display-recording-verification.md`](W05_C_live-display-recording-verification.md) | Current closeout and missing-evidence register | Partial closeout; CLI/GUI G1 PASS at documented revisions; final-artifact G1 repeat and G2 open |

The v01 preflight, protocol, host-transport and virtual-bench reports are historical snapshots. Their dated reconciliation notes govern current status; original test outputs are retained. See the [Week-6 plan](../../../week-06/submissions/module-c-ege/W06_C_spectrogram-recording-metadata.md).
