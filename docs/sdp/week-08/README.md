# EEE495 -- Week 8 -- Phantom Frequency Response and Latency

- **Theme:** Phantom Frequency Response and Latency (`9–15 Nov 2026` — Midterm Pause)
- **Status as of 2026-11-17:** `PARTIAL` (Module C automated metrology scripts, FRF/SNR/repeatability/hum/latency math & firmware bound audit verified in software on `2026-11-17`; Module A physical phantom FRF & Module B latency/30-min physical endurance bench runs `NOT_EXECUTED`)

## Submission Structure

| Folder | Owner | Module | Current Status |
|---|---|---|---|
| `submissions/module-a-kaan/` | Kaan | A -- Acquisition Hardware and Characterisation | **PENDING / NOT_EXECUTED** ([W08_A_phantom-frequency-response.md](submissions/module-a-kaan/W08_A_phantom-frequency-response.md)) |
| `submissions/module-b-ozan/` | Ozan | B -- Embedded Acquisition and Data Path | **PENDING / NOT_EXECUTED** ([W08_B_latency-continuous-run.md](submissions/module-b-ozan/W08_B_latency-continuous-run.md) — current firmware caps sessions at `G1_TARGET_SAMPLES=480000U` $\approx 10\text{ s}$) |
| `submissions/module-c-ege/` | Ege | C -- Computer Application and Quality Assessment | **SOFTWARE PIPELINE VERIFIED / PHYSICAL PENDING** ([W08_C_automated-measurement-script.md](submissions/module-c-ege/W08_C_automated-measurement-script.md)) |

## Decisions & Notes

- See [decisions.md](decisions.md) and [`PROGRESS_ASOF_2026-11-17.md`](../PROGRESS_ASOF_2026-11-17.md).
- Do not fabricate measurements or claim a 30-minute physical run before firmware session limits are explicitly lifted and verified on hardware.
