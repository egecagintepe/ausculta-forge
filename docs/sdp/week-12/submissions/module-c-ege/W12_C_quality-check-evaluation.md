# W12 Module C: Quality Check Evaluation

- **Week:** 12
- **Module:** C (Computer Application & Quality Assessment)
- **Owner:** Ege
- **Status:** PLANNED (Software Foundation Ready / Physical Data NOT_EXECUTED)

## Objective

Quantify detection rate, false-positive behavior, and 50 Hz mains interference rejection across physical phantom and ambient lab recordings prior to interim protocol freeze.

## Inputs / Dependencies

- Physical 50 Hz mains interference captures from Module A (`W12_A_mains-interference-test.md` — `NOT_EXECUTED`).
- Protocol freeze sign-off from Module B (`W12_B_protocol-freeze.md` — `NOT_EXECUTED`).
- Existing software foundations:
  - `software/pcg_core/scientific/signal_quality.py` (`evaluate_quality_detection_benchmark`)
  - `software/pcg_core/metrology/workflows.py` (`compute_mains_interference`)
  - `software/tests/test_scientific_signal_quality.py`

## Work Performed

- Physical Week 12 50 Hz mains characterization and field-artifact evaluation are **NOT_EXECUTED**.
- Software benchmark runner `evaluate_quality_detection_benchmark` has been implemented and tested against synthetic baseline + injected perturbations (`clipping`, `contact_loss`, `mains_interference`, `high_frequency_noise`, `packet_drop_discontinuity`), explicitly stamped `mode: "SOFTWARE_CONTROLLED_ARTIFACT_BENCHMARK"` and `physical_phantom_execution: "NOT_EXECUTED"`.

## Evidence

- Source modules: `software/pcg_core/scientific/signal_quality.py`, `software/pcg_core/metrology/workflows.py`
- Tests: `software/tests/test_scientific_signal_quality.py`
- Progress tracker: [`PROGRESS_ASOF_2026-11-17.md`](../../../PROGRESS_ASOF_2026-11-17.md)

## Results

- Physical detection confusion matrix & 50 Hz mains reduction measurements: **NOT_EXECUTED**.
- Software synthetic benchmark suite: `5/5` (`100.0%`) synthetic cases detected with `0` clean-baseline false positives in unit tests (`SOFTWARE_CONTROLLED_ARTIFACT_BENCHMARK` only).

## Open Decisions / Risks

- Synthetic `5/5` verification only proves algorithmic detector responsiveness on mathematical perturbations; real transducer self-noise and clinical skin/clothing friction still require physical Week 12 testing.

## Next Week Handoff

Summarize verified empirical evaluation metrics in Week 13 interim report generation (`W13_C_interim-report-software-evaluation.md`).
