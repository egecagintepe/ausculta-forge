# W09 Module C: Source Capture Comparison — Physical G2 Acceptance & Spectral Evaluation

- **Week:** 9 (16–22 Kasım 2026)
- **Date of Lab Execution & Evaluation:** 18 Kasım 2026
- **Module:** C (Computer Application & Quality Assessment)
- **Owner:** Ege Çağın Tepe
- **Status:** COMPLETED (Physical G2 Acceptance & SVD/Welch Evaluation) / PHANTOM COMPARISON PENDING

## Objective

Evaluate, verify, and document physical G2 INMP441 I²S audio acquisitions from ESP32-S3 over native USB CDC against reference quality standards; verify G1 dual-mode rollback determinism; perform spectral (Welch PSD), dynamic range, startup transient, and clipping analyses on real lab returns; and maintain clean repository evidence integrity.

## Inputs / Dependencies

- Physical lab return package from Kaan & Ozan (`AuscultaForge_Lab_Return_Kaan_Ozan_20261118_093859Z.zip` and `100114Z.zip`).
- Signal quality and validation engine (`software/pcg_core/validation.py`, `software/pcg_core/scientific/signal_quality.py`).
- Bring-up CLI tool (`software/bringup.py`).
- Pre-compiled release artifacts (`firmware/releases/g2_candidate_20261117/`).

## Work Performed

1. **Deterministic Verification of Lab Return Archives:**
   - Validated structural integrity of the field return ZIPs (142/142 files matched SHA256SUMS.txt bit-for-bit).
   - Re-computed and verified SHA-256 hashes of all raw WAV files, session JSON manifests, and firmware build manifests.
2. **Dual-Mode G1 Pre/Post Flash Verification:**
   - Pre-flash G1 verification (`20261118T090212Z_5e7113d0`): 480,000 samples, 1,875 blocks, 0 sequence discontinuities, 0 value errors (`PHYSICAL_G1_PASSED`).
   - Post-flash G1 verification (`20261118T091801Z_750cfd3e`): 480,000 samples, 1,875 blocks, 0 errors (`PHYSICAL_G1_PASSED`).
   - Confirms that the G2 candidate firmware maintains robust dual-mode backward compatibility without regressing synthetic reference capabilities.
3. **Physical G2 Quiet vs. Stimulus Evaluation:**
   - **Quiet Baseline (`session_20261118_091909_9e6baa63`):** 48 kHz, 10.0 s, 480,000 samples, mono float32. Total RMS: 0.0828.
     - *Startup Transient Finding:* Identified that the first 100 ms has RMS ≈ 0.4982 due to I²S DMA FIFO initialization and analog high-pass DC-blocking settling. Steady-state (1–5 s) RMS settles cleanly to **0.0156**. Documented that steady-state RMS must be used as the true noise floor reference.
   - **Acoustic Stimulus (`session_20261118_093225_19cde788`):** 48 kHz, 10.0 s, 480,000 samples. Total RMS: 0.2397, steady-state RMS: 0.2224. Peak: **0.999982 FS**.
     - *Spectral Power Ratio:* Welch PSD power ratio between stimulus and quiet sessions in the 20–500 Hz cardiac band was measured at **23.2 dB** (and ~24.7 dB via independent 4th-order Butterworth bandpass filtering).
4. **Resolution of Quality Metrics Discrepancy (Clipping vs. Saturation):**
   - Investigated why `bringup.py qualify` raised `clipping_detected = True` while `saturation_fraction = 0.0`.
   - Identified that `saturation_fraction` strictly checks hard ceiling (`|x| >= 0.9999`), which had only 6 samples (0.0013%), whereas `clipping_detected` flagged samples with `|x| > 0.98` (0.2775%, 1,332 samples).
   - Concluded: The acoustic loudspeaker test tone was played at high amplitude, driving the MEMS transducer to the edge of its linear dynamic range.
5. **DMA Telemetry Clarification:**
   - Proved that `dropped_samples = 256` reported in firmware telemetry equals `post_target_drained_samples = 256` (the final leftover 256-sample DMA buffer drained at STOP boundary), while `in_stream_dropped_samples = 0`. Zero data loss occurred during transmission.
6. **Provenance & Version Verification:**
   - Correlated lab execution baseline `319fcc59` with current repo HEAD `93f18ef`. Verified that the flashed binary SHA-256 hashes match repository release files bit-for-bit.

## Evidence

- `experiments/hardware/team_2026-11-18/RETURN_EVIDENCE_SUMMARY.json` — Consolidated evidence summary.
- `experiments/hardware/team_2026-11-18/PHYSICAL_G2_ACCEPTANCE_REPORT.md` — Formal engineering acceptance report.
- `experiments/hardware/team_2026-11-18/wednesday_g2_comparison.json` & `wednesday_g2_comparison.md` — Quantitative comparison data.
- Session manifests: `session_quiet_9e6baa63.json`, `session_stimulus_19cde788.json`, `session_stimulus_4888e670.json`, `session_stimulus_4e58ac08.json`.

## Results

- **Data Integrity:** **PASS** — 100% loss-free capture over USB CDC across 1.92M samples.
- **Dual-Mode Stability:** **PASS** — G1 deterministic test verified before and after flash.
- **Acoustic Responsiveness:** **PASS** — 23.2 dB SNR in 20–500 Hz band confirms physical transduction.
- **Acoustic Calibration & Clinical Stethoscope Status:** **PENDING** — Absolute dB SPL calibration, phantom frequency response, and clinical heart sound verification remain open for future sprints.

## Open Decisions / Risks

1. **Startup Transient Handling:** Future firmware and desktop software should mute or discard the first ~100–150 ms of I²S stream to prevent audio pop/artifact during display and metric computation.
2. **Clipping Guardband:** Host application should present an intuitive visual VU meter with warning levels for near-clipping (> -0.5 dBFS).
3. **Physical Phantom Comparison:** Real S1/S2 reference waveform playback through an acoustic phantom remains PENDING for Week 10.

## Next Week Handoff

Deliver verified physical G2 acquisition pipeline and quality analysis tools to Week 10 for automated acoustic phantom frequency sweep comparisons and real-time PCG segmentation integration.
