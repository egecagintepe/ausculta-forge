# W09 Module C: Source Capture Comparison

- **Week:** 9
- **Module:** C (Computer Application & Quality Assessment)
- **Owner:** Ege Çağın Tepe
- **Status:** SOFTWARE FRAMEWORK & CONTROLLED BENCHMARK READY / PHYSICAL FEASIBILITY GATE PENDING (Wednesday 2026-11-18)

## Objective

Provide quantitative comparison between a reference waveform and a captured recording (cross-correlation lag, least-squares gain, SER, NRMSE, coherence, and band energy ratios) plus objective multidimensional quality checks (clipping, contact-loss/VLF motion, mains hum, high-frequency noise, and packet drop continuity), ready for Week-9 S1/S2 phantom feasibility assessment.

## Inputs / Dependencies

- Reference-vs-capture validation engine (`software/pcg_core/validation.py`, `software/pcg_core/validate_capture.py`) and phantom alignment (`software/pcg_core/phantom.py`).
- Controlled artifact injection & detection benchmark added on 2026-11-17 in `software/pcg_core/scientific/signal_quality.py`.
- Physical dependency: Wednesday 2026-11-18 H0/G1/G2 physical INMP441 acquisition by Kaan & Ozan, followed by phantom feasibility capture.

## Work Performed

1. **Reference-vs-Capture Comparison & System ID (`software/pcg_core/validation.py`, `software/pcg_core/validate_capture.py`, `software/pcg_core/phantom.py`):**
   - Implemented cross-correlation delay estimation, least-squares and RMS gain ratios, NRMSE, signal-to-error ratio (SER), dominant frequency diff, band-energy diffs, and ordinary magnitude-squared coherence (`estimate_siso_system_id`).
2. **Controlled Artifact Injection & Quality Benchmark (`software/pcg_core/scientific/signal_quality.py`, added 2026-11-17):**
   - Implemented `inject_controlled_artifact` (`clipping`, `contact_loss`, `mains_interference`, `high_frequency_noise`) and `evaluate_quality_detection_benchmark` (covering all 4 signal artifacts plus `packet_drop_discontinuity`).
   - Unit tests verify `100%` detection (`5 / 5`) on synthetic distorted PCG signals with `0` false positives on clean baseline (`SOFTWARE_CONTROLLED_ARTIFACT_BENCHMARK`, no physical claim).
3. **Real ESP32-S3 G1 Hardware Device Center Acquisition & WAV Comparison Check (2026-11-16):**
   - Executed end-to-end Device Center acquisition (`COM10`, UID `0xb1aa7cc4`, `source_mode=1` G1 deterministic, **no microphone connected**) recording `session_20261116_112812_40d70550/raw.wav` (`194,304` samples, `4.048 s`, `48000 Hz`, mono `float32`, SHA-256 `9c9760d41e060e01f61b7fa486e76e6e14ebe9f7c1a4c7d9b6ea8066e0bd59e1`). Re-opened WAV matched metadata count and IEEE float32 range exactly (`0` dropped blocks).

## Evidence

- Source modules: `software/pcg_core/validation.py`, `software/pcg_core/validate_capture.py`, `software/pcg_core/phantom.py`, `software/pcg_core/scientific/signal_quality.py`
- Tests: `software/tests/test_validation.py`, `software/tests/test_scientific_signal_quality.py`, `software/tests/test_phantom_system_id.py`
- Tracked 2026-11-16 G1 + Device Center WAV evidence summary: [`laptop_20261116_g1_and_wav_summary.json`](../../../../../firmware/evidence/laptop_20261116_g1_and_wav_summary.json) (captures gitignored local WAV session `experiments/sessions/session_20261116_112812_40d70550/`, `194,304` samples, `4.048 s`, `physical_deterministic_g1`)
- Staged firmware packages (`COMPILED_BUT_NOT_FLASHED` / `PREPARED_NOT_AUTHORIZED_FOR_FLASH`): [`g1_release_20261117`](../../../../../firmware/releases/g1_release_20261117/README.md), [`g2_candidate_20261117`](../../../../../firmware/releases/g2_candidate_20261117/README.md)
- Progress & handoff docs: [`PROGRESS_ASOF_2026-11-17.md`](../../../PROGRESS_ASOF_2026-11-17.md), [`SDP4_WEEK01_06_DRAFT_PROGRESS_REPORT.md`](../../../SDP4_WEEK01_06_DRAFT_PROGRESS_REPORT.md), [`START_HERE_2026-11-18.md`](../../../../handoff/START_HERE_2026-11-18.md)

## Results

- Reference comparison, coherence, and controlled synthetic artifact benchmark are verified in software.
- **Physical Week-9 S1/S2 phantom feasibility test:** `PENDING` / `NOT_EXECUTED` (awaiting Wednesday 2026-11-18 physical INMP441 G2 bring-up and subsequent phantom assembly).

## Open Decisions / Risks

- **Feasibility Gate:** Physical INMP441 low-frequency roll-off (~60 Hz typical) and mechanical chestpiece coupling must be empirically checked on the physical phantom before moving to Week 10 comparisons. Do not advance if recognizable S1/S2 morphology is absent on real phantom capture.

## Next Week Handoff

Execute the Wednesday G2 bring-up (`docs/handoff/AGENT_WEDNESDAY_2026-11-18.md`), verify `g2-quiet` vs `g2-stimulus` with `bringup.py qualify`, and then capture physical phantom PCG replay vs reference WAV for comparison.
