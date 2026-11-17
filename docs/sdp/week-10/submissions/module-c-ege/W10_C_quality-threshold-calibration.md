# W10 Module C: Quality Threshold Calibration

- **Week:** 10
- **Module:** C (Computer Application & Quality Assessment)
- **Owner:** Ege
- **Status:** PLANNED (Software Foundation Ready / Physical Data NOT_EXECUTED)

## Objective

Calibrate automated signal quality thresholds (clipping, contact loss / VLF motion, 50 Hz mains contamination, high-frequency noise, and packet drop continuity) and acoustic filter preset boundaries against multi-transducer phantom recordings collected in Week 10.

## Inputs / Dependencies

- Physical transducer comparison recordings from Module A (`W10_A_transducer-comparison.md` — `NOT_EXECUTED`).
- Physical hardware gain/filter control support from Module B (`W10_B_gain-filter-control-support.md` — `NOT_EXECUTED`).
- Existing software foundations:
  - `software/pcg_core/scientific/signal_quality.py` (`SignalQualityConfig`, `assess_signal_quality`)
  - `software/pcg_core/analysis.py` (`FilterConfig`: `characterization_20_500hz`, `general_20_600hz`)
  - `software/pcg_app/protocol.py` & `software/frontend/src/audio/audioEngine.ts` (clinical presets `recommended` `[20, 200] Hz`, `bell` `[20, 120] Hz`, `diaphragm` `[100, 500] Hz`, `extended` `[20, 600] Hz`, verified by `software/frontend/src/audio/filter_transfer_response.test.ts`)

## Work Performed

- Future Week 10 calibration on live multi-transducer physical recordings is **NOT_EXECUTED**.
- Software filter presets, causal SOS Butterworth filtering (`StreamingBandpass` in `software/pcg_core/dsp.py`), and baseline `SignalQualityConfig` thresholds have already been implemented and unit-tested in software as preparation.
- Note: Historical Sprint 10 embedded interoperability documentation exists separately in [W10_C_embedded-interoperability-audit_v01.md](W10_C_embedded-interoperability-audit_v01.md) (preserved with timeline clarification).

## Evidence

- Source modules: `software/pcg_core/scientific/signal_quality.py`, `software/pcg_core/dsp.py`, `software/pcg_core/analysis.py`, `software/pcg_app/protocol.py`
- Progress tracker: [`PROGRESS_ASOF_2026-11-17.md`](../../../PROGRESS_ASOF_2026-11-17.md)

## Results

- Physical calibration status: **NOT_EXECUTED** (awaiting Week 10 phantom + dual-transducer physical recordings).

## Open Decisions / Risks

- Final clinical thresholds must only be locked using empirical physical microphone floor and phantom SNR distributions, never tuned solely on synthetic signals.

## Next Week Handoff

Once physical Week 10 captures are recorded, evaluate calibrated thresholds against controlled artifact injections in Week 11 (`W11_C_controlled-artifact-injection.md`).
