# W11 Module C: Controlled Artifact Injection

- **Week:** 11
- **Module:** C (Computer Application & Quality Assessment)
- **Owner:** Ege
- **Status:** PLANNED (Software Foundation Ready / Physical Data NOT_EXECUTED)

## Objective

Run controlled artifact injection experiments and statistical repeatability analyses to verify signal-quality detector robustness across realistic perturbations without corrupting raw unmodified reference recordings.

## Inputs / Dependencies

- Physical 10+ repeatability recordings from Module A (`W11_A_repeatability-test.md` — `NOT_EXECUTED`).
- Physical USB/DMA stress captures from Module B (`W11_B_buffer-stress-test.md` — `NOT_EXECUTED`).
- Existing software foundations:
  - `software/pcg_core/scientific/signal_quality.py` (`inject_controlled_artifact`, supporting `clipping`, `contact_loss`, `mains_interference`, `high_frequency_noise`)
  - `software/pcg_core/metrology/workflows.py` (`compute_repeatability_study`: mean, sample SD, CV%, 95% Student-$t$ CI)
  - `software/tests/test_scientific_signal_quality.py`

## Work Performed

- Physical Week 11 repeatability and real-recording artifact sweeps are **NOT_EXECUTED**.
- Software helper `inject_controlled_artifact` (`SOFTWARE_SYNTHETIC_ARTIFACT_INJECTION`) and repeatability statistical functions (`compute_repeatability_study`) have been implemented and covered by unit tests ahead of physical lab runs.

## Evidence

- Source modules: `software/pcg_core/scientific/signal_quality.py`, `software/pcg_core/metrology/workflows.py`
- Tests: `software/tests/test_scientific_signal_quality.py`, `software/tests/test_metrology_automation.py`
- Progress tracker: [`PROGRESS_ASOF_2026-11-17.md`](../../../PROGRESS_ASOF_2026-11-17.md)

## Results

- Physical repeatability & real-sensor stress results: **NOT_EXECUTED**.
- Software synthetic helper & repeatability math: implemented and tested as preparatory tooling (`physical_phantom_execution: "NOT_EXECUTED"`).

## Open Decisions / Risks

- Physical repeatability requires fixing acoustic excitation level, distance, and coupling pressure before running `compute_repeatability_study`.

## Next Week Handoff

Feed physical repeatability captures and injected-artifact confusion cases into Week 12 evaluation (`W12_C_quality-check-evaluation.md`).
