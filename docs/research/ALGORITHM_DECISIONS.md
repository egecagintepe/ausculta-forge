# AuscultaForge — Algorithm Decisions & Governance Log

Every candidate algorithm in AuscultaForge must receive one of five explicit classifications:
1. **`CORE_NOW`** — Active in production, tested, and mathematically documented.
2. **`NEXT_DSP`** — Scheduled for immediate implementation in upcoming DSP iterations.
3. **`RESEARCH_LATER`** — Requires literature maturation and system identification modeling.
4. **`THESIS_ONLY`** — Academic background for the capstone report; not in production software.
5. **`REJECTED`** — Formally excluded due to scientific invalidity or clinical safety violations.

---

## 1. Decision Registry Table

| Algorithm / Technique | Status | Literature Source | Primary Module | Decision Rationale & Boundaries |
|---|---|---|---|---|
| **Butterworth IIR Bandpass (20–600 Hz)** | `CORE_NOW` | R001, R002 | `pcg_core.dsp` | Maximally flat passband; eliminates sensor DC drift (<20 Hz) and high-frequency noise (>600 Hz). Clearly labeled engineering preset. |
| **Rational Resampling (`resample_poly`)** | `CORE_NOW` | R002 | `pcg_core.validation` | Polyphase rational rate matching. Ensures capture is cleanly matched to reference rate before alignment. |
| **Normalized Cross-Correlation Delay Estimation** | `CORE_NOW` | R001, R002 | `pcg_core.validation` | Quantifies bulk transmission delay between excitation and capture. |
| **Least-Squares Gain Estimator ($\hat{g}$)** | `CORE_NOW` | R001, R002 | `pcg_core.validation` | Optimal scalar linear gain estimator under aligned LTI model; resilient to zero-mean additive noise unlike RMS gain. |
| **Welch Power Spectral Density** | `CORE_NOW` | R003, R004 | `pcg_core.streaming`, `analysis` | Nonparametric averaged periodograms with explicit windowing, detrending, and ENBW scaling. |
| **Magnitude-Squared Coherence ($\gamma^2(f)$)** | `CORE_NOW` | R001, R002 | `pcg_core.validation` | Evaluates degree of linear relationship across frequency; highlights noise/non-linearity in 20–600 Hz band. |
| **Peak-Preserving Shared-Time Decimation** | `CORE_NOW` | Empirical Metrology | `pcg_app.analysis_service` | Protects browser UI responsiveness while preserving narrow S1/S2 extrema and guaranteeing pointwise error identity. |
| **Hilbert Transform Envelope** | `NEXT_DSP` | R001, R006 | Stage A Roadmap | Analytic signal magnitude $A(t) = \sqrt{x^2(t) + \mathcal{H}\{x\}^2(t)}$; captures instantaneous acoustic energy envelope. |
| **Homomorphic Envelope Extraction** | `NEXT_DSP` | R001, R005, R006 | Stage A Roadmap | Log-envelope low-pass filtering; separates slow cardiac sound envelope from fast acoustic carrier ripples. |
| **RMS / Sliding Energy Envelope** | `NEXT_DSP` | R001 | Stage A Roadmap | Short-term energy windowing ($20\text{--}50\text{ ms}$) for acoustic event candidate detection. |
| **Four-State HSMM Duration Model (LR-HSMM)** | `RESEARCH_LATER` | R005, R006, R007 | Stage B Roadmap | Requires multi-feature training and logistic regression emission probabilities. Deferred until Stage A feature engine is complete. |
| **Frequency Response Estimators ($H_1, H_2$)** | `RESEARCH_LATER` | R002, Bendat & Piersol | Phantom Backlog | Requires dedicated broadband acoustic excitation protocol and acoustic impedance standard. |
| **Automated Clinical AI Diagnosis** | `REJECTED` | FDA / CE Regulations | None | AuscultaForge is an engineering validation and research platform, NOT a medical diagnostic tool. |
| **Universal "Quality Score" (e.g. 85/100)** | `REJECTED` | Metrological Canon | None | Subjective aggregate scores mask separate physical failure modes (drops, clipping, noise, drift). |
| **Uncalibrated Acoustic Units ($\text{Pa}, \text{dB SPL}$)** | `REJECTED` | R003, Metrology | None | Strictly prohibited without physical transducer sensitivity calibration ($\text{mV/Pa}$ or $\text{dBFS/Pa}$). |
| **2D Image Processing for 1D Audio** | `REJECTED` | R008 | None | Morphological 2D image operators from R008 do not apply directly to 1D acoustic time-series. |

---

## 2. In-Depth Decision Records

### Decision 2026-01: Butterworth 20–600 Hz Bandpass (`CORE_NOW`)
- **Physical Problem:** Raw acoustic sensors capture DC baseline drift, breathing movement (<20 Hz), and high-frequency ambient noise (>600 Hz).
- **Mathematical Model:** 4th-order IIR Butterworth filter designed via bilinear transform with maximally flat passband $|H(e^{j\omega})| = \frac{1}{\sqrt{1 + (\omega / \omega_c)^{2N}}}$.
- **Assumptions:** Phase non-linearity in the transition band is acceptable for visualization and energy envelope estimation.
- **Literature Basis:** Rangayyan (R001, Ch. 3 & 4), Oppenheim & Schafer (R002, Ch. 7).
- **Configuration:** Causal SOS realization in `StreamingBandpass`. Offline zero-phase filtering (`sosfiltfilt`) must be explicitly declared if ever used.

### Decision 2026-02: Least-Squares Gain vs RMS Gain Ratio (`CORE_NOW`)
- **Physical Problem:** Transducer amplifiers, acoustic loss, and coupling attenuate signal amplitude. Additive noise inflates RMS calculations.
- **Mathematical Model:** Given aligned $y[n] = g \cdot x[n] + v[n]$, minimize $E(g) = \sum (y[n] - g \cdot x[n])^2 \implies \hat{g} = \frac{\sum x[n] y[n]}{\sum x[n]^2}$.
- **Assumptions:** Noise $v[n]$ is uncorrelated with reference $x[n]$ ($\mathbb{E}[x \cdot v] = 0$).
- **Literature Basis:** Oppenheim & Schafer (R002, Ch. 11), Heinzel et al. (R003).
- **Configuration:** Production UI displays Least-Squares Gain as the primary linear scale metric and adds an explicit warning tooltip on RMS Gain Ratio.

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
| **aliasing** | R002 (Oppenheim & Schafer Ch. 4) | `IMPLEMENTED` | Guarded by 48 kHz Nyquist limit (24 kHz) & polyphase anti-aliasing in `resample_poly` | `test_validation.py` | `SCIENTIFIC_CONVENTIONS.md` |
| **quantization** | R002 (Ch. 4 Sec. 4.8), R003 | `IMPLEMENTED` | `pcg_core.models`, `pcg_app.device_runtime` (24-bit meaningful in 32-bit container, $Q=24$ noise floor) | `test_device_runtime.py`, `test_scientific_config.py` | `UNITS_AND_CALIBRATION.md` |
| **Butterworth filter** | R001 (Ch. 3), R002 (Ch. 7) | `IMPLEMENTED` | `pcg_core.dsp.StreamingBandpass` (4th-order 20–600 Hz IIR SOS) | `test_dsp.py` | `SCIENTIFIC_CONVENTIONS.md`, `ALGORITHM_DECISIONS.md` |
| **causal filtering** | R002 (Oppenheim & Schafer Ch. 2, 5) | `IMPLEMENTED` | `pcg_core.dsp.StreamingBandpass.process_chunk` (causal stateful `sosfilt`) | `test_dsp.py` | `SCIENTIFIC_CONVENTIONS.md`, `MATH_CONVENTIONS.md` |
| **resampling** | R002 (Oppenheim & Schafer Ch. 4 Sec. 4.6) | `IMPLEMENTED` | `pcg_core.validation.match_sampling_rates` (polyphase rational resampling via `resample_poly`) | `test_validation.py` | `SCIENTIFIC_CONVENTIONS.md`, `MATH_CONVENTIONS.md` |
| **Welch PSD** | R003 (Heinzel), R004 (Welch 1967) | `IMPLEMENTED` | `pcg_core.streaming.LiveSpectralAnalyzer`, `pcg_core.scientific_config.SpectralAnalysisConfig` | `test_streaming.py`, `test_scientific_config.py` | `SCIENTIFIC_CONVENTIONS.md`, `MATH_CONVENTIONS.md` |
| **windowing** | R002 (Ch. 10), R003 (Heinzel Sec. 4) | `IMPLEMENTED` | `SpectralAnalysisConfig.window` (Hann default, Hamming, Flattop, Boxcar) | `test_scientific_config.py` | `SCIENTIFIC_CONVENTIONS.md`, `MATH_CONVENTIONS.md` |
| **ENBW** | R003 (Heinzel et al. Eq. 18) | `IMPLEMENTED` | `pcg_core.scientific_config.SpectralAnalysisConfig.enbw` (exact $f_s \frac{\sum w^2}{(\sum w)^2}$) | `test_scientific_config.py` | `SCIENTIFIC_CONVENTIONS.md`, `MATH_CONVENTIONS.md` |
| **DC detrending** | R003 (Heinzel et al. Sec. 7) | `IMPLEMENTED` | `pcg_core.scientific_config.DetrendMode`, `pcg_core.streaming` (`constant`, `linear`, `none`) | `test_scientific_config.py` | `SCIENTIFIC_CONVENTIONS.md`, `MATH_CONVENTIONS.md` |
| **RMS** | R001 (Ch. 4), R003 (Sec. 2) | `IMPLEMENTED` | `pcg_core.validation.compute_rms` ($\sqrt{\frac{1}{N}\sum x^2[n]}$) | `test_validation.py` | `MATH_CONVENTIONS.md` |
| **band energy** | R001 (Rangayyan Ch. 6 Sec. 6.3) | `IMPLEMENTED` | `pcg_core.dsp.compute_frequency_band_fractions`, `validation` (0–20, 20–150, 150–600, >600 Hz) | `test_dsp.py`, `test_validation.py` | `SCIENTIFIC_CONVENTIONS.md`, `MATH_CONVENTIONS.md` |
| **cross-correlation** | R001 (Ch. 4), R002 (Ch. 2, 11) | `IMPLEMENTED` | `pcg_core.validation.estimate_time_delay` (`scipy.signal.correlate`) | `test_validation.py` | `MATH_CONVENTIONS.md` |
| **delay estimate** | R001, R002 | `IMPLEMENTED` | `pcg_core.validation.estimate_time_delay` (lag maximizing NCC; positive = capture delayed) | `test_validation.py` | `MATH_CONVENTIONS.md` |
| **least-squares gain** | R001, R002 (Ch. 11) | `IMPLEMENTED` | `pcg_core.validation.estimate_linear_gain` ($\hat{g} = (x^T y)/(x^T x)$) | `test_validation.py` | `MATH_CONVENTIONS.md`, `ALGORITHM_DECISIONS.md` |
| **RMSE** | R001, R002 | `IMPLEMENTED` | `pcg_core.validation.compute_rmse` ($\sqrt{\frac{1}{N}\sum (y[n] - \hat{g}x[n])^2}$) | `test_validation.py` | `MATH_CONVENTIONS.md` |
| **NRMSE** | R001, Metrological Canon | `IMPLEMENTED` | `pcg_core.validation.compute_nrmse` ($\text{RMSE} / (\max y - \min y)$) | `test_validation.py` | `MATH_CONVENTIONS.md` |
| **SER** | R001, R002 | `IMPLEMENTED` | `pcg_core.validation.compute_ser_db` ($10 \log_{10} \frac{\sum (\hat{g}x)^2}{\sum (y - \hat{g}x)^2}$) | `test_validation.py` | `MATH_CONVENTIONS.md` |
| **coherence** | R001 (Ch. 6 Sec. 6.4), R002 (Ch. 10, 11) | `IMPLEMENTED` | `pcg_core.validation.compute_spectral_coherence` (`scipy.signal.coherence`) | `test_validation.py` | `MATH_CONVENTIONS.md` |
| **Hilbert envelope** | R001 (Ch. 4), R002 (Ch. 12), R006 | `PLANNED` | Stage A DSP Engine roadmap ($A(t) = \sqrt{x^2 + \mathcal{H}\{x\}^2}$) | Scheduled | `SCIENTIFIC_CONVENTIONS.md`, `R006-springer-logistic-regression-hsmm.md` |
| **homomorphic envelope** | R001 (Ch. 4), R005, R006 | `PLANNED` | Stage A DSP Engine roadmap ($\exp(\text{LPF}\{\ln(\|x[n]\| + \epsilon)\})$) | Scheduled | `SCIENTIFIC_CONVENTIONS.md`, `R005-schmidt-duration-dependent-hmm.md` |
| **PSD envelope** | R006 (Springer et al. 2016) | `PLANNED` | Stage A DSP Engine roadmap (spectrogram time-slice power envelope) | Scheduled | `SCIENTIFIC_CONVENTIONS.md`, `R006-springer-logistic-regression-hsmm.md` |
| **four-state PCG model** | R005, R006, R007 | `PARTIAL` | State definitions established (`S1`, `SYSTOLE`, `S2`, `DIASTOLE`); HMM decoder pending | Pending | `SCIENTIFIC_CONVENTIONS.md`, `ALGORITHM_DECISIONS.md` |
| **HSMM duration model** | R005, R006 | `RESEARCH_ONLY` | Theoretical formulation documented; deferred to Stage B roadmap | None | `R006-springer-logistic-regression-hsmm.md`, `SCIENTIFIC_CONVENTIONS.md` |
| **modified Viterbi** | R006 (Springer et al. 2016) | `RESEARCH_ONLY` | Duration-dependent forward-backward dynamic programming; deferred to Stage B | None | `R006-springer-logistic-regression-hsmm.md`, `SCIENTIFIC_CONVENTIONS.md` |
| **segmentation tolerance evaluation** | R007 (Liu et al. 2019) | `RESEARCH_ONLY` | Multi-database evaluation protocol defined; deferred to Stage C | None | `R007-liu-hsmm-independent-database-evaluation.md`, `SCIENTIFIC_CONVENTIONS.md` |
| **phantom LTI approximation** | R002 (Ch. 2), Bendat & Piersol | `PARTIAL` | `pcg_core.validation` ($y[n] = h[n]*x[n] + v[n]$); physical non-linearities uncharacterized | `test_validation.py` | `THEORY_MAP.md`, `MATH_CONVENTIONS.md` |

