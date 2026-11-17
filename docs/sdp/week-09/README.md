# EEE495 -- Week 9 -- Feasibility and Continuity Verification

- **Theme:** Feasibility and Continuity Verification (`16–22 Nov 2026` — Active As-Of `2026-11-17`)
- **Status as of 2026-11-17:** `PARTIAL` (`2026-11-16` G1 COM10 `480,000`-sample pass + Device Center real G1 WAV verified; `2026-11-17` G1/G2 ESP-IDF v5.5.1 builds, controlled artifact benchmark, and Git-free Wednesday lab handoff staged; Wednesday `2026-11-18` Module A/B physical G2 + phantom feasibility session `PENDING`)

## Submission Structure

| Folder | Owner | Module | Current Status |
|---|---|---|---|
| `submissions/module-a-kaan/` | Kaan | A -- Acquisition Hardware and Characterisation | **PENDING** ([W09_A_feasibility-test.md](submissions/module-a-kaan/W09_A_feasibility-test.md) — Wednesday `2026-11-18` H0 + phantom/mic feasibility session) |
| `submissions/module-b-ozan/` | Ozan | B -- Embedded Acquisition and Data Path | **PARTIAL** ([W09_B_continuity-clipping-verification.md](submissions/module-b-ozan/W09_B_continuity-clipping-verification.md) — `2026-11-16` G1 zero-loss COM10 run verified by Ege; Ozan physical G2 mic continuity/clipping check pending) |
| `submissions/module-c-ege/` | Ege | C -- Computer Application and Quality Assessment | **SOFTWARE READY / 2026-11-16 G1 WAV VERIFIED / PHYSICAL G2 PENDING** ([W09_C_source-capture-comparison.md](submissions/module-c-ege/W09_C_source-capture-comparison.md)) |

## Tracked Evidence & Wednesday Lab Links

- [Tracked 2026-11-16 G1 + Device Center WAV Evidence Summary](../../../firmware/evidence/laptop_20261116_g1_and_wav_summary.json)
- [Staged G1 Release (`COMPILED_BUT_NOT_FLASHED`)](../../../firmware/releases/g1_release_20261117/README.md) & [Staged G2 Candidate (`PREPARED_NOT_AUTHORIZED_FOR_FLASH`)](../../../firmware/releases/g2_candidate_20261117/README.md)
- [Wednesday Physical Lab Start Guide (`START_HERE_2026-11-18.md`)](../../handoff/START_HERE_2026-11-18.md) & [As-Of 2026-11-17 Progress Summary](../PROGRESS_ASOF_2026-11-17.md)
- See [decisions.md](decisions.md) for open and resolved decisions.

## Notes

- Today (`2026-11-17`) no physical board is attached; today's USB run status is `NOT_EXECUTED`.
- Do not fabricate measurements or label `2026-11-16` synthetic G1 WAV captures as real microphone audio.
