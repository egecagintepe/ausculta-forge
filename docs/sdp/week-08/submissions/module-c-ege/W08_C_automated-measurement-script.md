# W08 Module C: Automated Measurement Script

- **Week:** 8
- **Module:** C (Computer Application & Quality Assessment)
- **Owner:** Ege Çağın Tepe
- **Status:** SOFTWARE PIPELINE VERIFIED / PHYSICAL BENCH MEASUREMENTS PENDING

## Objective

Implement automated, reproducible measurement scripts and CLI workflows that ingest captured WAV recordings and stream telemetry logs, compute the project characterization tables (FRF, coherence, SNR, repeatability, mains hum, latency, and drop continuity), and generate machine-readable reports without mixing simulated checks with physical data.

## Inputs / Dependencies

- `software/pcg_core/scientific/system_id.py` (`estimate_siso_system_id`), `software/pcg_core/scientific/signal_quality.py`, `software/pcg_core/phantom.py`.
- Physical dependency: live G2 USB recordings, phantom sweeps, and Module B endurance captures (not yet executed).

## Work Performed

1. **Advisor Metrology Automation Pipeline (`software/pcg_core/metrology/`):**
   - `cli.py`: CLI entrypoint supporting `--generate-template`, `--config`, `--synthetic`, and `--output-dir` JSON/CSV/Markdown generation.
   - `workflows.py`:
     - `compute_phantom_frf` (SISO $H_1$ magnitude/phase and coherence over `20–500 Hz`).
     - `compute_active_quiescent_snr` (band-limited `20–500 Hz` RMS ratio).
     - `compute_repeatability_study` (mean, sample SD, CV%, 95% Student-$t$ CI over $\ge 10$ runs).
     - `compute_mains_interference` (`<= 0.5 Hz` Welch PSD resolution over 50 Hz harmonics).
     - `compute_latency_measurement` (explicitly separates unsynchronized acoustic lag from hardware-synced trigger/loopback measurements).
     - `compute_continuity_drop_rate` (packet sequence continuity and 30-minute gate audit).
2. **First-Contact & Recording Qualification CLI (`tools/hardware/bringup.py`, `software/pcg_app/hardware_workflow.py`):**
   - `qualify_recording` validates mono float32 WAV integrity, SHA-256, `DC`, `RMS`, `peak`, saturation fraction, and Welch PSD while stamping `"physical_microphone": "NOT_VERIFIED_BY_THIS_ANALYSIS"` and `"acoustic_frequency_response": "NOT_MEASURED"`.
3. **Host Throughput Benchmark & Protocol Boundary Audit (`scripts/benchmark_host_pipeline.py`, `firmware/components/g1/include/g1.h`):**
   - Documented current firmware `G1_TARGET_SAMPLES = 480000U` (`10.0 s` @ `48 kHz`) and `g1_tick()` 40 s session timeout cap (`firmware/components/g1/g1.c:192`). No false 30-minute endurance claim is made.

## Evidence

- Source modules: `software/pcg_core/metrology/{cli.py,runner.py,workflows.py,models.py,reports.py}`, `software/pcg_core/phantom.py`, `software/pcg_app/hardware_workflow.py`, `tools/hardware/bringup.py`
- Tests: `software/tests/test_metrology_automation.py`, `software/tests/test_phantom_system_id.py`, `software/tests/test_streaming_performance.py`, `software/tests/test_first_contact.py`
- Handoff report: [`docs/sdp/PROGRESS_ASOF_2026-11-17.md`](../../../PROGRESS_ASOF_2026-11-17.md)

## Results

- Metrology CLI and mathematical workflows pass synthetic self-tests (`MeasurementStatus.SYNTHETIC_BENCH_TEST` / `test_metrology_automation.py`, `test_phantom_system_id.py`).
- **Physical phantom FRF, live latency, and 30-minute continuous endurance:** `NOT_EXECUTED` (physical G2 microphone not yet connected; firmware currently enforces a 10 s / 480,000-sample bounded target per acquisition session).

## Open Decisions / Risks

- **30-Minute Endurance Constraint:** Before attempting a physical 30-minute continuous acquisition in Module B/C, firmware `G1_TARGET_SAMPLES` (`480000U` = 10 s) and the 40-second `g1_tick()` timeout cap must be consciously lifted or chunked under an explicit endurance test mode.

## Next Week Handoff

Use `bringup.py qualify` on Wednesday's initial G2 quiet and stimulus captures first, then supply `--config` WAV inputs to `python -m pcg_core.metrology.cli` once phantom sweep and repeatability runs exist.
