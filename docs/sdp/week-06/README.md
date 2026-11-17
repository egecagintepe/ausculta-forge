# EEE495 -- Week 6 -- Characterisation Round 1 (26 Oct – 1 Nov 2026)

- **Theme:** Characterisation Round 1
- **Overall Status:** `PARTIAL` (Physical G1 PASS on 2026-10-26; Module C Desktop/Spectral/Audio PASS; Module A Transducer Bench & Physical G2 INMP441 PENDING)

## Submission Structure & Status (Week 6 Window)

| Folder | Owner | Module | Status as of 2026-11-17 |
|---|---|---|---|
| `submissions/module-a-kaan/` | Kaan | A -- Acquisition Hardware and Characterisation | **PENDING** ([W06_A_first-transducer-gain-bandwidth.md](submissions/module-a-kaan/W06_A_first-transducer-gain-bandwidth.md) — physical bench deferred past midterms to 2026-11-18) |
| `submissions/module-b-ozan/` | Ozan (Official) / Ege (Code) | B -- Embedded Acquisition and Data Path | **G1: PASS (2026-10-26)** / **G2 Physical Mic: PENDING** — Physical ESP32 G1 (`480,000` samples, 0 drops) ran 2026-10-26 (`106d3e0`, `59d773e`); `i2s_source.c` unit-tested (`16/16`); immutable G1 backup archived in [`firmware/g1_rollback_backup/`](../../../firmware/g1_rollback_backup/README.md). |
| `submissions/module-c-ege/` | Ege | C -- Computer Application and Quality Assessment | **PASS (Software & Audio)** — See [W06_C_spectrogram-recording-metadata.md](submissions/module-c-ege/W06_C_spectrogram-recording-metadata.md) and [`WEEK6_SPRINT_REPORT.md`](../../engineering/release/WEEK6_SPRINT_REPORT.md). |

## Decisions & Evidence Links

- Week-6 Decisions: [decisions.md](decisions.md)
- Sprint & Offline PCG Evidence: [`WEEK6_SPRINT_REPORT.md`](../../engineering/release/WEEK6_SPRINT_REPORT.md) | [`WEEK6_OFFLINE_REAL_PCG_REPORT.md`](../../engineering/release/WEEK6_OFFLINE_REAL_PCG_REPORT.md) | [`WEEK6_AUTONOMOUS_NATIVE_AUDIO_ACCEPTANCE.md`](../../engineering/release/WEEK6_AUTONOMOUS_NATIVE_AUDIO_ACCEPTANCE.md)
- Academic Summary: [SDP4_WEEK01_06_DRAFT_PROGRESS_REPORT.md](../SDP4_WEEK01_06_DRAFT_PROGRESS_REPORT.md#hafta-6-26-ekim--1-kasım-2026)

## Notes

- Physical 2026-10-26 G1 testing belongs chronologically to Week 6 and is not backdated into Week 5.
- Real microphone G2 (`source_mode=0`) was not executed physically in Week 6 and remains `PENDING`.
