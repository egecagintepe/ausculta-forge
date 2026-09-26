# AuscultaForge — Algorithm Decisions & Governance Log

Every candidate algorithm in AuscultaForge must receive one of five explicit classifications:
1. **`CORE_NOW`** — Active in production, tested, and mathematically documented.
2. **`NEXT_DSP`** — Scheduled for immediate implementation in upcoming DSP iterations.
3. **`RESEARCH_LATER`** — Requires literature maturation and system identification modeling.
4. **`THESIS_ONLY`** — Academic background for the capstone report; not in production software.
5. **`REJECTED`** — Formally excluded due to scientific invalidity or clinical safety violati## 1. Decision Registry Table

| Algorithm / Technique | Status | Literature Source | Primary Module | Decision Rationale & Boundaries |
|---|---|---|---|---|
| **Butterworth IIR Bandpass (20–600 Hz)** | `CORE_NOW` | R001, R002 | `pcg_core.dsp.StreamingBandpass` | Maximally flat passband; eliminates sensor DC drift (<20 Hz) and high-frequency noise (>600 Hz). Provisional engineering development preset, NOT a clinical standard. |
| **Rational Resampling (`resample_poly`)** | `CORE_NOW` | R002 | `pcg_core.validation.validate_signals` | Polyphase rational rate matching via `scipy.signal.resample_poly`. Ensures capture is cleanly matched to reference rate before alignment. |
| **Raw Cross-Correlation Delay Estimation** | `CORE_NOW` | R001, R002 | `pcg_core.validation.estimate_delay_and_align` | Evaluates peak of raw cross-correlation between capture and reference (`scipy.signal.correlate`). Positive delay means capture lags reference. |
| **Least-Squares Gain Estimator ($\hat{g}$)** | `CORE_NOW` | R001, R002 | `pcg_core.validation.compute_least_squares_gain` | Optimal scalar linear gain estimator under aligned LTI model ($\hat{g} = (x^T y)/(x^T x)$); reported as separate linear scale metric. |
| **Welch Power Spectral Density** | `CORE_NOW` (Math) / `PARTIAL` (Runtime Integration) | R003, R004 | `pcg_core.streaming.compute_spectral_frame`, `pcg_core.scientific_config` | Averaged periodograms. `SpectralAnalysisConfig` model implemented; live streaming runtime integration is partial. |
| **Magnitude-Squared Coherence ($\gamma^2(f)$)** | `CORE_NOW` | R001, R002 | `pcg_core.validation.validate_signals` | Evaluates degree of linear relationship across frequency via `scipy.signal.coherence`; mean evaluated over 20–600 Hz passband. |
| **Peak-Preserving Shared-Time Decimation** | `CORE_NOW` | Empirical Metrology | `pcg_app.analysis_service.decimate_aligned_traces_shared_time` | Protects browser UI responsiveness while preserving narrow S1/S2 extrema and guaranteeing pointwise error identity at identical timestamps. |
| **Hilbert Transform Envelope** | `NEXT_DSP` | R001, R006 | Stage A Roadmap | Analytic signal magnitude $A(t) = \sqrt{x^2(t) + \mathcal{H}\{x\}^2(t)}$; captures instantaneous acoustic energy envelope. |
| **Homomorphic Envelope Extraction** | `NEXT_DSP` | R001, R005, R006 | Stage A Roadmap | Log-envelope low-pass filtering; separates slow cardiac sound envelope from fast acoustic carrier ripples. |
| **RMS / Sliding Energy Envelope** | `NEXT_DSP` | R001 | Stage A Roadmap | Short-term energy windowing ($20\text{--}50\text{ ms}$) for acoustic event candidate detection. |
| **Four-State HSMM Duration Model (LR-HSMM)** | `RESEARCH_LATER` | R005, R006, R007 | Stage B Roadmap | Requires multi-feature training and logistic regression emission probabilities. Deferred until Stage A feature engine is complete. |
| **Frequency Response Estimators ($H_1, H_2$)** | `RESEARCH_LATER` | R002, Bendat & Piersol | Phantom Backlog | Requires dedicated broadband acoustic excitation protocol and acoustic impedance standard. |
| **Automated Clinical AI Diagnosis** | `REJECTED` | FDA / CE Regulations | None | AuscultaForge is an engineering validation and research platform, NOT a medical diagnostic tool. |
| **Universal "Quality Score" (e.g. 85/100)** | `REJECTED` | Metrological Canon | None | Subjective aggregate scores mask separate physical failure modes (drops, clipping, noise, drift). |
| **Uncalibrated Acoustic Units ($\text{Pa}, \text{dB SPL}$)** | `REJECTED` | R003, Metrology | None | Strictly prohibited without a documented calibrated acoustic measurement chain ($\text{mV/Pa}$ or $\text{dBFS/Pa}$). |
| **2D Image Processing for 1D Audio** | `REJECTED` | R008 | None | Morphological 2D image operators from R008 do not apply directly to 1D acoustic time-series. |

---

## 2. In-Depth Decision Records

### Decision 2026-01: Butterworth 20–600 Hz Bandpass (`CORE_NOW`)
- **Physical Problem:** Raw acoustic sensors capture DC baseline drift, breathing movement (<20 Hz), and high-frequency ambient noise (>600 Hz).
- **Mathematical Model:** 4th-order IIR Butterworth filter designed via bilinear transform with maximally flat passband $|H(e^{j\omega})| = \frac{1}{\sqrt{1 + (\omega / \omega_c)^{2N}}}$.
- **Assumptions:** Phase non-linearity in the transition band is acceptable for visualization and energy envelope estimation.
- **Literature Basis:** Literature supports PCG filtering and frequency-domain characterization (Rangayyan R001, Ch. 3 & 4; Oppenheim & Schafer R002, Ch. 7). AuscultaForge 20–600 Hz is a provisional/general engineering development preset, NOT an externally validated clinical standard.
- **Configuration:** Causal SOS realization in `StreamingBandpass.process()`. Offline zero-phase filtering (`sosfiltfilt`) must be explicitly declared in metadata if ever used.

### Decision 2026-02: Least-Squares Gain vs RMS Gain Ratio (`CORE_NOW`)
- **Physical Problem:** Transducer amplifiers, acoustic loss, and coupling attenuate signal amplitude. Additive noise inflates RMS calculations.
- **Mathematical Model:** Given aligned sequences, compute $\hat{g} = \frac{\sum x[n] y[n]}{\sum x[n]^2}$ in `compute_least_squares_gain()`.
- **Assumptions:** Noise $v[n]$ is uncorrelated with reference $x[n]$ ($\mathbb{E}[x \cdot v] = 0$).
- **Literature Basis:** Oppenheim & Schafer (R002, Ch. 11), Heinzel et al. (R003).
- **Configuration:** Production UI displays Least-Squares Gain as the primary linear scale metric and adds an explicit warning tooltip on RMS Gain Ratio. Note: Current code computes RMSE directly on $y_{\text{aligned}} - x_{\text{aligned}}$ without removing $\hat{g}$.

### Decision 2026-03: Staged PCG Segmentation Roadmap (`NEXT_DSP` & `RESEARCH_LATER`)
- **Physical Problem:** Locating S1, Systole, S2, Diastole in the cardiac acoustic cycle.
- **Staging Decision:**
  - **Stage A (`NEXT_DSP`):** Deterministic envelope extractors (Hilbert, Homomorphic, Energy). Independent of machine learning models.
  - **Stage B (`RESEARCH_LATER`):** Logistic Regression HSMM reproduction strictly following Springer et al. (R006).
  - **Stage C (`RESEARCH_LATER`):** Cross-database validation and tolerance window evaluation strictly following Liu et al. (R007).

---

## 3. Comprehensive Research Traceability Matrix

Every core signal processing and PCG concept is tracked across literature, implementation, tests, and documentation.
Statuses strictly use: `IMPLEMENTED`, `PARTIAL`, `PLANNED`, `RESEARCH_ONLY`, `NOT_IMPLEMENTED`.

| Concept | Source | Status | Current Implementation | Tests | Documentation |
|---|---|---|---|---|---|
| **sampling** | R002 (Oppenheim & Schafer Ch. 4) | `IMPLEMENTED` | `pcg_app.device_runtime`, `pcg_core.scientific_config` (48 kHz Rev-A master, $T_s = 1/f_s$) | `test_device_runtime.py`, `test_scientific_config.py` | `SCIENTIFIC_CONVENTIONS.md`, `MATH_CONVENTIONS.md` |
| **aliasing** | R002 (Oppenheim & Schafer Ch. 4) | `PARTIAL` | Digital anti-aliasing via `scipy.signal.resample_poly` inside `validate_signals`; hardware analog front-end anti-aliasing unverified | `test_validation.py` | `SCIENTIFIC_CONVENTIONS.md` |
| **quantization** | R002 (Ch. 4 Sec. 4.8), R003 | `IMPLEMENTED` | `pcg_core.models.SampleBlock`, `pcg_app.device_runtime` (24 transmitted data bits in 32-bit container; sensor effective precision unverified) | `test_device_runtime.py`, `test_scientific_config.py` | `UNITS_AND_CALIBRATION.md` |
| **Butterworth filter** | R001 (Ch. 3), R002 (Ch. 7) | `IMPLEMENTED` | `pcg_core.dsp.StreamingBandpass` (4th-order 20–600 Hz IIR SOS; provisional engineering preset) | `test_dsp.py` | `SCIENTIFIC_CONVENTIONS.md`, `ALGORITHM_DECISIONS.md` |
| **causal filtering** | R002 (Oppenheim & Schafer Ch. 2, 5) | `IMPLEMENTED` | `pcg_core.dsp.StreamingBandpass.process` (causal stateful `scipy.signal.sosfilt`) | `test_dsp.py` | `SCIENTIFIC_CONVENTIONS.md`, `MATH_CONVENTIONS.md` |
| **resampling** | R002 (Oppenheim & Schafer Ch. 4 Sec. 4.6) | `IMPLEMENTED` | Polyphase rational rate matching via `scipy.signal.resample_poly` inside `pcg_core.validation.validate_signals` | `test_validation.py` | `SCIENTIFIC_CONVENTIONS.md`, `MATH_CONVENTIONS.md` |
| **Welch PSD** | R003 (Heinzel), R004 (Welch 1967) | `PARTIAL` | `pcg_core.scientific_config.SpectralAnalysisConfig` (model IMPLEMENTED); live runtime integration in `compute_spectral_frame` uses default Welch call (PARTIAL) | `test_streaming.py`, `test_scientific_config.py` | `SCIENTIFIC_CONVENTIONS.md`, `MATH_CONVENTIONS.md` |
| **windowing** | R002 (Ch. 10), R003 (Heinzel Sec. 4) | `IMPLEMENTED` | `SpectralAnalysisConfig.window` (Hann default, Hamming, Flattop, Boxcar); default Hann in runtime streaming | `test_scientific_config.py` | `SCIENTIFIC_CONVENTIONS.md`, `MATH_CONVENTIONS.md` |
| **ENBW** | R003 (Heinzel Section 4) | `PARTIAL` | `pcg_core.scientific_config.SpectralAnalysisConfig.enbw` ($f_s \frac{\sum w^2}{(\sum w)^2}$) IMPLEMENTED; live streaming frame reporting NOT_IMPLEMENTED | `test_scientific_config.py` | `SCIENTIFIC_CONVENTIONS.md`, `MATH_CONVENTIONS.md` |
| **DC detrending** | R003 (Heinzel Sec. 7) | `PARTIAL` | `pcg_core.scientific_config.DetrendMode` enum model IMPLEMENTED; runtime selectable streaming detrending NOT_IMPLEMENTED | `test_scientific_config.py` | `SCIENTIFIC_CONVENTIONS.md`, `MATH_CONVENTIONS.md` |
| **RMS** | R001 (Ch. 4), R003 (Sec. 2) | `IMPLEMENTED` | `pcg_core.metrics.rms` ($\sqrt{\frac{1}{N}\sum x^2[n]}$) | `test_core.py`, `test_validation.py` | `MATH_CONVENTIONS.md` |
| **band energy** | R001 (Rangayyan Ch. 6 Sec. 6.3) | `IMPLEMENTED` | `pcg_core.dsp.compute_frequency_band_fractions`, `pcg_core.analysis.compute_spectrogram_data` (AuscultaForge engineering partitions: 0–20, 20–150, 150–600, >600 Hz) | `test_dsp.py`, `test_analysis.py` | `SCIENTIFIC_CONVENTIONS.md`, `MATH_CONVENTIONS.md` |
| **cross-correlation** | R001 (Ch. 4), R002 (Ch. 2, 11) | `IMPLEMENTED` | `scipy.signal.correlate` inside `pcg_core.validation.estimate_delay_and_align` | `test_validation.py` | `MATH_CONVENTIONS.md` |
| **delay estimate** | R001, R002 | `IMPLEMENTED` | `pcg_core.validation.estimate_delay_and_align` (argmax of raw cross-correlation; positive = capture delayed) | `test_validation.py` | `MATH_CONVENTIONS.md` |
| **least-squares gain** | R001, R002 (Ch. 11) | `IMPLEMENTED` | `pcg_core.validation.compute_least_squares_gain` ($\hat{g} = (x^T y)/(x^T x)$) | `test_validation.py` | `MATH_CONVENTIONS.md`, `ALGORITHM_DECISIONS.md` |
| **RMSE** | R001, R002 | `IMPLEMENTED` | Evaluated in `pcg_core.validation.validate_signals` on $y_{\text{aligned}} - x_{\text{aligned}}$ without removing $\hat{g}$ ($\sqrt{\frac{1}{M}\sum (y[n] - x[n])^2}$) | `test_validation.py` | `MATH_CONVENTIONS.md` |
| **NRMSE** | R001, Metrological Canon | `IMPLEMENTED` | Evaluated in `pcg_core.validation.validate_signals` ($\text{RMSE} / \text{RMS}(x_{\text{aligned}})$) | `test_validation.py` | `MATH_CONVENTIONS.md` |
| **SER** | R001, R002 | `IMPLEMENTED` | Evaluated in `pcg_core.validation.validate_signals` ($10 \log_{10} \frac{\sum x_{\text{aligned}}^2}{\sum (y_{\text{aligned}} - x_{\text{aligned}})^2}$ with 100 dB finite cap) | `test_validation.py` | `MATH_CONVENTIONS.md` |
| **coherence** | R001 (Ch. 6 Sec. 6.4), R002 (Ch. 10, 11) | `IMPLEMENTED` | `scipy.signal.coherence` inside `pcg_core.validation.validate_signals` (mean evaluated over 20–600 Hz passband) | `test_validation.py` | `MATH_CONVENTIONS.md` |
| **Hilbert envelope** | R001 (Ch. 4), R002 (Ch. 12), R006 | `PLANNED` | Stage A DSP Engine roadmap ($A(t) = \sqrt{x^2 + \mathcal{H}\{x\}^2}$) | Scheduled | `SCIENTIFIC_CONVENTIONS.md`, `R006-springer-logistic-regression-hsmm.md` |
| **homomorphic envelope** | R001 (Ch. 4), R005, R006 | `PLANNED` | Stage A DSP Engine roadmap ($\exp(\text{LPF}\{\ln(\|x[n]\| + \epsilon)\})$) | Scheduled | `SCIENTIFIC_CONVENTIONS.md`, `R005-schmidt-duration-dependent-hmm.md` |
| **PSD envelope** | R006 (Springer et al. 2016) | `PLANNED` | Stage A DSP Engine roadmap (spectrogram time-slice power envelope) | Scheduled | `SCIENTIFIC_CONVENTIONS.md`, `R006-springer-logistic-regression-hsmm.md` |
| **four-state PCG model** | R005, R006, R007 | `PARTIAL` | State definitions established (`S1`, `SYSTOLE`, `S2`, `DIASTOLE`); HMM decoder pending | Pending | `SCIENTIFIC_CONVENTIONS.md`, `ALGORITHM_DECISIONS.md` |
| **HSMM duration model** | R005, R006 | `RESEARCH_ONLY` | Theoretical formulation documented; deferred to Stage B roadmap | None | `R006-springer-logistic-regression-hsmm.md`, `SCIENTIFIC_CONVENTIONS.md` |
| **modified Viterbi** | R006 (Springer et al. 2016) | `RESEARCH_ONLY` | Duration-dependent forward-backward dynamic programming; deferred to Stage B | None | `R006-springer-logistic-regression-hsmm.md`, `SCIENTIFIC_CONVENTIONS.md` |
| **segmentation tolerance evaluation** | R007 (Liu et al. 2019) | `RESEARCH_ONLY` | Multi-database evaluation protocol defined; deferred to Stage C | None | `R007-liu-hsmm-independent-database-evaluation.md`, `SCIENTIFIC_CONVENTIONS.md` |
| **phantom LTI approximation** | R002 (Ch. 2), Bendat & Piersol | `PARTIAL` | `pcg_core.validation` ($y[n] = h[n]*x[n] + v[n]$); physical non-linearities and coupling uncharacterized | `test_validation.py` | `THEORY_MAP.md`, `MATH_CONVENTIONS.md` |
