# AuscultaForge — Week 10 Laboratory Metrology and Measurement Plan

**Document Date:** 2026-11-25  
**Course:** EEE 495 / SDP4 — Smart Digital Stethoscope  
**Author:** AuscultaForge Engineering Team (Kaan, Ozan, Ege)  
**Status:** Software Verified / Physical Laboratory Execution Pending (25 November 2026)

---

## 1. Official Course Mapping (Reconciled with `SDP4_Digital_Stethoscope_Plan_EN.docx`)

All experimental protocols and status labels strictly follow the official Semester I (EEE 495) schedule:
- **Status Vocabulary:** `VERIFIED SOFTWARE`, `VERIFIED PHYSICAL`, `PARTIAL`, `PENDING`, `NOT EXECUTED`, `INCONCLUSIVE`.

| Week | Official Plan (`SDP4_Digital_Stethoscope_Plan_EN.docx`) | Current Verification Status |
|---|---|---|
| **Week 5** | **A:** Build first breadboard front end; measure noise floor with input shorted.<br>**B:** Bring up dev board; stream synthetic waveform to computer; confirm zero lost samples.<br>**C:** Build live display and recording function; verify with synthetic stream. | **A:** `PARTIAL` (digital MEMS INMP441 used instead of analog AFE breadboard; quiet baseline captured 18 Nov).<br>**B:** `VERIFIED PHYSICAL` (G1 synthetic ramp 480,000 samples @ 48 kHz, 0 drops, 18 Nov).<br>**C:** `VERIFIED SOFTWARE` (live workspace, recording, integrity manifest). |
| **Week 6** | **A:** Connect first transducer; measure gain and bandwidth with function generator.<br>**B:** Replace synthetic source with real converter input; verify timestamp continuity.<br>**C:** Add spectrogram view and recording library with metadata fields. | **A:** `PARTIAL` (physical transducer connected; swept-sine bandwidth on phantom scheduled 25 Nov).<br>**B:** `VERIFIED PHYSICAL` (G2 live `source_mode=0` INMP441, 4 $\times$ 10s runs on 18 Nov, 1.92M samples).<br>**C:** `VERIFIED SOFTWARE` (spectrogram & session library verified). |
| **Week 7** | **A:** Build acoustic phantom (small transducer under compliant layer + chestpiece).<br>**B:** Implement device status reporting and packet loss detection.<br>**C:** Implement playback path so dataset recording can be driven into phantom. | **A:** `PENDING` (RTV-2 poured 23 Nov, cure check 25 Nov; chestpiece/transfer plate assembly on bench).<br>**B:** `VERIFIED PHYSICAL` (Profile B telemetry, CRC-32, sequence tracking).<br>**C:** `VERIFIED SOFTWARE` (`PlaybackController`, stimulus generator). |
| **Week 8** | **A:** Measure frequency response of complete chain on phantom using swept signal.<br>**B:** Measure end-to-end latency and run continuous acquisition $\ge 30\text{ min}$.<br>**C:** Implement automated test script that records, measures, and writes results table. | **A:** `NOT EXECUTED` (scheduled 25 Nov post-P0).<br>**B:** `NOT EXECUTED` physically (endurance software candidate `run_endurance_session.py` ready; G2 release preserved for P0).<br>**C:** `VERIFIED SOFTWARE` (`run_phantom_pcg_experiment.py`). |
| **Week 9 (P0)** | **Feasibility Gate:** Phonocardiogram played through phantom must be captured with recognisable S1/S2 structure. Confirm continuous, timestamped, clipping-free capture and numerical similarity. | **Software:** `VERIFIED SOFTWARE` (14/14 anti-false-pass & morphology tests passing).<br>**Physical:** `PENDING` (Primary P0 objective for 25 Nov morning lab). |
| **Week 10** | **A:** Compare two transducer candidates on phantom under identical conditions.<br>**B:** Add adjustable gain or filter modes if supported.<br>**C:** Implement recording quality check and calibrate thresholds on phantom recordings. | **A/B:** `NOT EXECUTED` (scheduled 25 Nov post-P0 if comparator available).<br>**C:** `VERIFIED SOFTWARE` (Butterworth Bell/Diaphragm filters & quality thresholds implemented; physical calibration pending). |

---

## 2. Reconciled Acceptance Thresholds (`run_phantom_pcg_experiment.py`)

| Gate | Metric | Acceptance Threshold | Failure / Inconclusive Condition |
|---|---|---|---|
| **Data Integrity** | Sequence gaps, CRC-32 errors, DMA/ring overflows, firmware drops | Strictly `0` gaps, `0` CRC errors, `0` overflows; `256` post-target drain accepted **only** when `generated_samples >= target_samples + 256` and all other telemetry is present and zero | Missing telemetry (`INCONCLUSIVE_MISSING_TELEMETRY`), incomplete samples, or any in-stream drop (`FAILED_*`) |
| **Signal & Clipping** | Peak amplitude, near-clipping fraction ($\ge 0.98\text{ FS}$), RMS | `peak < 0.99 FS`, `near_clipping < 0.05%`, `RMS > 1e-6 FS` | Silence/constant (`FAILED_SILENCE_OR_CONSTANT_SIGNAL`) or saturation (`FAILED_CLIPPING`) |
| **In-Band SNR** | Active-to-quiet band power ratio ($20\text{--}500\text{ Hz}$) vs. fresh `--quiet-session` | $\ge 12.0\text{ dB}$ | Missing quiet session (`INCONCLUSIVE_NO_QUIET_BASELINE`), zero quiet RMS (`INCONCLUSIVE_QUIET_ZERO_OR_INVALID`), or $< 12.0\text{ dB}$ |
| **Alignment & Overlap** | Normalized Cross-Correlation (NCC) & overlap window | `NCC >= 0.35` and `overlap >= 50%` of signal length | `FAILED_INSUFFICIENT_OVERLAP` or `FAILED_LOW_CORRELATION` |
| **Passband Coherence** | Welch magnitude-squared coherence ($20\text{--}250\text{ Hz}$) | $\ge 0.40$ | `FAILED_LOW_COHERENCE` |
| **Envelope Morphology** | One-to-one Shannon-envelope burst match ($\pm 80\text{ ms}$ tolerance) | Match fraction $\ge 70.0\%$, mean jitter $\le 45.0\text{ ms}$, contrast $\ge 2.0$ | `INCONCLUSIVE_*` (Note: generic envelope complexes matched to reference; independent S1/S2 valve labeling requires clinical ground truth) |
| **Playback & Routing** | `PlaybackController` completion & `--verify-audio-routing` | Completed without timeout/abort/error + explicit operator routing attestation | `FAILED_TIMEOUT`, `FAILED_ABORTED`, or `UNVERIFIED` routing |

---

## 3. Mathematical Formulations & Latency Separation

- **Transfer Function ($H_1$):** $H_1(f) = \frac{S_{xy}(f)}{S_{xx}(f)}$, Welch PSD ($N_{\text{win}}=4096$, 50% overlap, Hanning).
- **Coherence:** $\gamma_{xy}^2(f) = \frac{|S_{xy}(f)|^2}{S_{xx}(f) S_{yy}(f)}$.
- **Active-to-Quiet Ratio:** $\text{SNR}_{20\text{--}500} = 10 \log_{10} \left(\frac{P_{\text{active}, 20\text{--}500}}{P_{\text{quiet}, 20\text{--}500}}\right)\text{ dB}$ (not calibrated dB SPL).
- **Latency Honesty:** Cross-correlation produces `estimated_recording_lag_ms` (which combines OS audio playback startup jitter, acoustic propagation, DMA framing, and USB transfer). `measured_end_to_end_latency_ms` remains `null` (`is_hardware_synchronized: false`) unless measured with a dedicated hardware loopback sync pulse.
- **INMP441 Low-Frequency Note:** Nominal $-3\text{ dB}$ corner near $60\text{ Hz}$ per datasheet; $20\text{--}60\text{ Hz}$ attenuation is annotated, never artificially equalized.

---

## 4. Safety & Regulatory Disclaimer

Academic research prototype for EEE 495 / EEE 496 only. Not a certified medical device; no human recordings; no mains connection.
