# AuscultaForge — Mathematical Conventions & Formulation Standards

This document establishes the project-wide mathematical notation, formulations, and operational definitions used across `pcg_core` and `pcg_app`.

---

## 1. Fundamental Time & Frequency Notation

| Symbol | Definition | Units | Notes |
|---|---|---|---|
| $t$ | Continuous time | $\text{seconds (s)}$ | Used in physical propagation models. |
| $x_c(t)$ | Continuous-time analog acoustic signal | Uncalibrated / Volts | Sound pressure incident on microphone diaphragm. |
| $n$ | Discrete sample index ($n \in \mathbb{Z}$) | Dimensionless integer | Zero-indexed sample count in discrete buffers. |
| $T_s$ | Sampling interval / period | $\text{seconds (s)}$ | Time between consecutive discrete samples. |
| $f_s$ | Sampling frequency ($f_s = 1 / T_s$) | $\text{Hertz (Hz)}$ | Hardware Rev-A standard: $48,000\text{ Hz}$. |
| $x[n]$ | Discrete-time digital reference signal | Dimensionless ($\text{FS}$) | Sampled sequence: $x[n] \equiv x_c(n T_s)$. |
| $y[n]$ | Discrete-time captured audio signal | Dimensionless ($\text{FS}$) | Acquired sequence from device or file. |
| $N$ | Number of samples in a finite window | Dimensionless integer | Length of block, window, or segment. |
| $k$ | Discrete frequency bin index ($0 \le k < N$) | Dimensionless integer | DFT / FFT frequency bin. |
| $\Delta f$ | Discrete frequency bin spacing ($\Delta f = f_s / N$) | $\text{Hertz (Hz)}$ | Minimum separable spectral frequency resolution. |
| $f$ | Continuous frequency variable | $\text{Hertz (Hz)}$ | Nyquist range: $0 \le f \le f_s / 2$. |

---

## 2. Statistical & Time-Domain Metrics

### 2.1. Sample Mean
$$\bar{x} = \frac{1}{N} \sum_{n=0}^{N-1} x[n]$$

### 2.2. Sample Variance & Standard Deviation
$$s_x^2 = \frac{1}{N-1} \sum_{n=0}^{N-1} (x[n] - \bar{x})^2, \quad \sigma_x = \sqrt{s_x^2}$$

### 2.3. Root Mean Square (RMS)
$$\text{RMS}(x) = \sqrt{\frac{1}{N} \sum_{n=0}^{N-1} x^2[n]}$$

### 2.4. Peak Absolute Amplitude
$$\text{Peak}(x) = \max_{0 \le n < N} |x[n]|$$

### 2.5. Crest Factor
$$\text{CF}(x) = \frac{\text{Peak}(x)}{\text{RMS}(x)}$$
*Measures peakiness relative to signal energy; useful for detecting sharp S1/S2 acoustic transients vs. flat noise.*

---

## 3. Signal Alignment & Engineering Comparison Metrics

All signal alignment and comparison metrics are implemented in `software/pcg_core/validation.py`.

### 3.1. Discrete Cross-Correlation for Delay Search
Delay estimation in `estimate_delay_and_align()` evaluates the raw cross-correlation between the captured sequence $y[n]$ and reference sequence $x[n]$ using `scipy.signal.correlate(cap, ref)`:
$$R_{yx}[m] = \sum_{n} y[n] x[n - m]$$
The lag index maximizing raw cross-correlation determines the estimated delay in samples:
$$D^* = \arg\max_{m} R_{yx}[m]$$
$$\text{delay\_ms} = \frac{D^*}{f_s} \times 1000.0$$

> **Sign Convention Invariant:**
> - $\text{delay} > 0$ means the capture lags behind the reference ($y[n + D^*]$ corresponds to $x[n]$).
> - $\text{delay} < 0$ means the capture leads the reference.
> - The lag search operates on raw cross-correlation; it is **NOT** a normalized cross-correlation peak search.

### 3.2. Reported Normalized Cross-Correlation (NCC)
After alignment over the overlapping window of length $M$, `validate_signals()` computes the reported NCC using **mean-centered signals and sample standard deviations** (the sample Pearson correlation coefficient):
$$\bar{x} = \frac{1}{M}\sum_{n=0}^{M-1} x_{\text{aligned}}[n], \quad \bar{y} = \frac{1}{M}\sum_{n=0}^{M-1} y_{\text{aligned}}[n]$$
$$s_x = \sqrt{\frac{1}{M}\sum_{n=0}^{M-1} (x_{\text{aligned}}[n] - \bar{x})^2}, \quad s_y = \sqrt{\frac{1}{M}\sum_{n=0}^{M-1} (y_{\text{aligned}}[n] - \bar{y})^2}$$
$$\text{NCC} = \frac{\frac{1}{M} \sum_{n=0}^{M-1} (x_{\text{aligned}}[n] - \bar{x}) (y_{\text{aligned}}[n] - \bar{y})}{s_x \cdot s_y} = \frac{\text{mean}\left((x_{\text{aligned}} - \bar{x})(y_{\text{aligned}} - \bar{y})\right)}{\text{std}(x_{\text{aligned}}) \cdot \text{std}(y_{\text{aligned}})}$$
- Range: $[-1.0, +1.0]$ (clipped to $[-1.0, 1.0]$ in code; evaluates to $1.0$ on exact match, $0.0$ if zero variance).
- Quantifies waveform shape similarity independent of DC bias and scalar amplitude scaling.
- Note: This is a centered Pearson correlation, **NOT** an uncentered cosine similarity.

### 3.3. Least-Squares Gain ($\hat{g}$)
Given aligned sequences, `compute_least_squares_gain()` determines the optimal scalar linear amplitude scaling factor $\hat{g}$ minimizing $\sum (y_{\text{aligned}}[n] - g \cdot x_{\text{aligned}}[n])^2$:
$$\hat{g} = \frac{\mathbf{x}^T \mathbf{y}}{\mathbf{x}^T \mathbf{x}} = \frac{\sum_{n=0}^{M-1} x_{\text{aligned}}[n] y_{\text{aligned}}[n]}{\sum_{n=0}^{M-1} x_{\text{aligned}}^2[n]}$$
- Reported as a separate amplitude-scaling metric.
- Unbiased under zero-mean additive noise uncorrelated with the reference signal, unlike the RMS gain ratio $\text{RMS}(y) / \text{RMS}(x)$ which is inflated by additive noise power.

### 3.4. Root Mean Square Error (RMSE)
Computed directly in `validate_signals()` on the difference between aligned signals:
$$e[n] = y_{\text{aligned}}[n] - x_{\text{aligned}}[n]$$
$$\text{RMSE} = \sqrt{\frac{1}{M} \sum_{n=0}^{M-1} \left(y_{\text{aligned}}[n] - x_{\text{aligned}}[n]\right)^2}$$
- **Current Implementation Note:** Current code evaluates RMSE directly on $y_{\text{aligned}} - x_{\text{aligned}}$. It does **NOT** subtract or remove the least-squares gain $\hat{g}$ before computing RMSE.

### 3.5. Normalized Root Mean Square Error (NRMSE)
Computed in `validate_signals()` by normalizing RMSE by the RMS of the aligned reference signal:
$$\text{NRMSE} = \frac{\text{RMSE}}{\text{RMS}(x_{\text{aligned}})}$$
- Dimensionless relative error.
- Range-normalized formulations (such as $\text{RMSE} / (\max y - \min y)$) are **NOT** used in AuscultaForge.

### 3.6. Signal-to-Error Ratio (SER, dB)
Computed in `validate_signals()` from reference energy and residual error energy:
$$\text{SER (dB)} = 10 \log_{10} \left( \frac{\sum_{n=0}^{M-1} x_{\text{aligned}}^2[n]}{\sum_{n=0}^{M-1} \left(y_{\text{aligned}}[n] - x_{\text{aligned}}[n]\right)^2} \right)$$
- **Finite Bounds:**
  - If error energy $\sum e^2[n] \le 10^{-15}$, SER is capped at $+100.0\text{ dB}$ (finite perfect match).
  - If reference energy $\sum x^2[n] \le 10^{-15}$, SER evaluates to $0.0\text{ dB}$.
- **Current Implementation Note:** Like RMSE, the residual in the denominator is $y_{\text{aligned}} - x_{\text{aligned}}$ without applying least-squares gain $\hat{g}$.


---

## 4. Spectral & Frequency-Domain Metrics

### 4.1. Discrete Fourier Transform (DFT)
$$X[k] = \sum_{n=0}^{N-1} x[n] w[n] e^{-j 2\pi k n / N}, \quad k = 0, 1, \dots, N-1$$

### 4.2. Welch Modified Periodogram Averaging
For $K$ windowed segments of length $L$ with overlap $D$:
$$\hat{P}_{xx}(f) = \frac{1}{K \cdot f_s \cdot S_2} \sum_{i=1}^K |X_i(f)|^2$$
where $S_2 = \sum_{n=0}^{L-1} w^2[n]$ is the window noise power normalization factor (Heinzel et al., R003).

### 4.3. Equivalent Noise Bandwidth (ENBW)
Formulation (Heinzel et al., R003, Section 4 / Window functions and metrics):
$$\text{ENBW} = f_s \cdot \frac{\sum_{n=0}^{L-1} w^2[n]}{\left(\sum_{n=0}^{L-1} w[n]\right)^2}$$

### 4.4. Band Energy Fraction
For a specified frequency band $[f_a, f_b]$:
$$\text{BER}_{[f_a, f_b]} = \frac{\int_{f_a}^{f_b} \hat{P}_{xx}(f) df}{\int_{0}^{f_s / 2} \hat{P}_{xx}(f) df}$$

### 4.5. Magnitude-Squared Coherence
$$\gamma_{xy}^2(f) = \frac{|P_{xy}(f)|^2}{P_{xx}(f) P_{yy}(f)}$$
- Range: $[0.0, 1.0]$.
- Measures the degree of linear causality between excitation and capture at each frequency $f$.
