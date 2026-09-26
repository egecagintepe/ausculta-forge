# AuscultaForge — Authoritative Research Source Registry

This document records the foundational scientific literature governing the AuscultaForge signal processing pipeline, spectral metrology, and segmentation roadmap.

---

## 1. Master Source Table

| Source ID | Citation Short Title | Primary Role / Domain | Project Authority Level | Direct File Link |
|---|---|---|---|---|
| **R001** | Rangayyan (2002 / 2015), *Biomedical Signal Analysis* | Biomedical DSP & PCG Characterization | **FOUNDATIONAL** | [R001 Dossier](file:///c:/Dev/Antigravity/bitirme/ausculta-forge/docs/research/sources/R001-rangayyan-biomedical-signal-analysis.md) |
| **R002** | Oppenheim & Schafer (2010), *Discrete-Time Signal Processing* | Theoretical DSP, Multirate, & Filters | **CANONICAL MATH** | [R002 Dossier](file:///c:/Dev/Antigravity/bitirme/ausculta-forge/docs/research/sources/R002-oppenheim-discrete-time-signal-processing.md) |
| **R003** | Heinzel et al. (2002), *Spectrum & Spectral Density Estimation* | PSD Scaling, ENBW, & Leakage Metrology | **METROLOGY CANON** | [R003 Dossier](file:///c:/Dev/Antigravity/bitirme/ausculta-forge/docs/research/sources/R003-heinzel-spectrum-estimation.md) |
| **R004** | Welch (1967), *Averaged Modified Periodograms* | Nonparametric Spectral Estimation | **METHOD CANON** | [R004 Dossier](file:///c:/Dev/Antigravity/bitirme/ausculta-forge/docs/research/sources/R004-welch-power-spectrum-estimation.md) |
| **R005** | Schmidt et al. (2010), *Duration-Dependent HMM* | Four-State PCG Segmentation Baseline | **SEGMENTATION BASELINE** | [R005 Dossier](file:///c:/Dev/Antigravity/bitirme/ausculta-forge/docs/research/sources/R005-schmidt-duration-dependent-hmm.md) |
| **R006** | Springer et al. (2016), *Logistic Regression-HSMM* | Modern PCG Feature Stream & LR-HSMM | **TARGET SEGMENTATION** | [R006 Dossier](file:///c:/Dev/Antigravity/bitirme/ausculta-forge/docs/research/sources/R006-springer-logistic-regression-hsmm.md) |
| **R007** | Liu et al. (2016), *Open Access Database Evaluation* | Cross-Database Validation & Tolerances | **VALIDATION BENCHMARK** | [R007 Dossier](file:///c:/Dev/Antigravity/bitirme/ausculta-forge/docs/research/sources/R007-liu-hsmm-independent-database-evaluation.md) |
| **R008** | Rangayyan (2005), *Biomedical Image Analysis* | 2D Image Morphology & Segmentation | **LOW DIRECT RELEVANCE** | [R008 Dossier](file:///c:/Dev/Antigravity/bitirme/ausculta-forge/docs/research/sources/R008-rangayyan-biomedical-image-analysis.md) |

---

## 2. Bibliographic Details & Scope

### R001 — Rangayyan, R. M. (2002 / 2015)
- **Full Title:** *Biomedical Signal Analysis: A Case-Study Approach* (1st Ed. 2002, 2nd Ed. 2015).
- **Publisher:** IEEE Press / John Wiley & Sons.
- **Role:** Primary biomedical PCG reference.
- **Key Thematic Coverage:**
  - Physiological origin and mechanical acoustics of S1, S2, S3, and S4 heart sounds.
  - PCG event characterization, time-domain activity measures, and amplitude envelopes.
  - Nonstationary PCG signal filtering, baseline wander removal, and muscle artifact rejection.
  - Fourier analysis, power spectral density, dominant frequency detection, and spectral power ratios.
  - Cross-spectral analysis and coherence for acoustic transmission systems.
- **Project Mapping:** Justifies the 20–600 Hz general PCG passband, spectral band ratios, and envelope feature extraction methods.

### R002 — Oppenheim, A. V., & Schafer, R. W. (2010)
- **Full Title:** *Discrete-Time Signal Processing* (3rd Edition).
- **Publisher:** Pearson Higher Education.
- **Role:** Primary mathematical signal-processing authority.
- **Key Thematic Coverage:**
  - Discrete-time LTI systems, linear convolution, and difference equations.
  - Sampling theorem, Nyquist criterion, aliasing, and multirate resampling theory.
  - ADC uniform quantization error model and quantization noise variance ($\sigma_e^2 = \Delta^2 / 12$).
  - IIR filter approximation, analog prototypes, and bilinear transformation (Butterworth filters).
  - Magnitude response, non-linear phase distortion, and group delay in causal filtering.
  - Discrete Fourier Transform (DFT), Fast Fourier Transform (FFT), and windowing trade-offs.
  - Random signals, autocorrelation, cross-correlation, and linear system estimation.
- **Project Mapping:** Underpins `pcg_core.dsp.StreamingBandpass`, `scipy.signal.resample_poly`, cross-correlation delay estimation, and least-squares gain.

### R003 — Heinzel, G., Rüdiger, A., & Schilling, R. (2002)
- **Full Title:** *Spectrum and spectral density estimation by the Discrete Fourier transform (DFT), including a comprehensive list of window functions and some new flat-top windows.*
- **Institution:** Max-Planck-Institut für Gravitationsphysik (Albert-Einstein-Institut), Teilinstitut Hannover, Technical Report MPI-186.
- **Role:** Metrological authority on practical DFT and PSD computation.
- **Key Thematic Coverage:**
  - Strict distinction between Power Spectrum ($\text{V}^2$ or $\text{FS}^2$) and Power Spectral Density ($\text{V}^2/\text{Hz}$ or $\text{FS}^2/\text{Hz}$).
  - Coherent gain ($S_1$) and noise power gain ($S_2$) for arbitrary window functions.
  - Equivalent Noise Bandwidth: $\text{ENBW} = f_s \cdot \frac{S_2}{S_1^2}$.
  - Window leakage, picket-fence effect, and amplitude error bounds.
  - Preprocessing DC subtraction and linear detrending to prevent low-frequency window smear.
- **Project Mapping:** Dictates `SpectralAnalysisConfig` scaling modes, ENBW computation, and detrending policies.

### R004 — Welch, P. D. (1967)
- **Full Title:** *The Use of Fast Fourier Transform for the Estimation of Power Spectra: A Method Based on Time Averaging Over Short, Modified Periodograms.*
- **Journal:** *IEEE Transactions on Audio and Electroacoustics*, AU-15(2), pp. 70–73.
- **Role:** Canonical method reference for non-parametric spectral estimation.
- **Key Thematic Coverage:**
  - Segmenting non-stationary or long records into overlapping windowed segments.
  - Modified periodogram computation via FFT.
  - Reduction of spectral variance by segment averaging: $\text{Var}\{\hat{P}_{xx}(f)\} \propto 1/K$.
- **Project Mapping:** Direct foundation of `scipy.signal.welch` and `pcg_core.streaming.compute_spectral_frame`.

### R005 — Schmidt, S. E., Holst-Hansen, C., Graff, C., Toft, E., & Struijk, J. J. (2010)
- **Full Title:** *Segmentation of heart sound recordings by a duration-dependent hidden Markov model.*
- **Journal:** *Physiological Measurement*, 31(4), pp. 513–529.
- **Role:** Baseline literature model for four-state PCG segmentation.
- **Key Thematic Coverage:**
  - Division of the cardiac cycle into four distinct states: $S_1 \rightarrow \text{Systole} \rightarrow S_2 \rightarrow \text{Diastole}$.
  - Specific preprocessing filter: 4th-order Butterworth bandpass at 25–400 Hz.
  - Homomorphic envelope extraction for acoustic event candidate generation.
  - Explicit modeling of state durations via Gaussian / Poisson duration probability distributions.
- **Project Mapping:** Provides the benchmark parameters for `PCG_EVENT_FEATURES_V1` and future Stage B reproduction.

### R006 — Springer, D. B., Tarassenko, L., & Clifford, G. D. (2016)
- **Full Title:** *Logistic Regression-HSMM-based Heart Sound Segmentation.*
- **Journal:** *IEEE Transactions on Biomedical Engineering*, 63(4), pp. 742–752.
- **Role:** Primary target research model for AuscultaForge PCG segmentation.
- **Key Thematic Coverage:**
  - Hidden Semi-Markov Model (HSMM) with explicit state duration probability distributions.
  - Logistic regression mapping from continuous feature vectors to state emission probabilities.
  - Four-feature acoustic envelope extraction downsampled to 50 Hz:
    1. Homomorphic envelope
    2. Hilbert envelope
    3. Wavelet envelope
    4. Power spectral density envelope
  - Modified Viterbi decoding algorithm tracking joint state and duration transitions.
- **Project Mapping:** Defines the roadmap for Stage A (deterministic feature extraction) and Stage B (LR-HSMM implementation).

### R007 — Liu, C., Springer, D. B., Li, Q., Moody, B., et al. (2016)
- **Full Title:** *An open access database for the evaluation of heart sound algorithms.*
- **Journal:** *Physiological Measurement*, 37(12), pp. 2181–2213.
- **Role:** Benchmark validation and evaluation authority.
- **Key Thematic Coverage:**
  - Multi-centre, heterogeneous PCG database evaluation (PhysioNet / CinC Challenge 2016).
  - Explicit tolerance windows for $S_1$ and $S_2$ event boundary matching ($\pm 60\text{ ms}$ or $\pm 100\text{ ms}$).
  - Metrics: Sensitivity ($Se$), Positive Predictive Value ($PPV$), and overall $F_1$ score.
  - Strict separation of training and test subjects to evaluate real-world generalization.
- **Project Mapping:** Governs the testing and scoring protocol for Stage C segmentation evaluation.

### R008 — Rangayyan, R. M. (2005)
- **Full Title:** *Biomedical Image Analysis.*
- **Publisher:** CRC Press.
- **Role:** Reference archive only — **LOW DIRECT RELEVANCE** for current 1D acoustic project.
- **Clarification:** Listed to acknowledge laboratory background literature; contains 2D spatial filtering, segmentation, and morphology algorithms not applicable to AuscultaForge's 1D acoustic stream.
