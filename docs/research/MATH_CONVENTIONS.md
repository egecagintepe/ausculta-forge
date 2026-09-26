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

### 3.1. Discrete Cross-Correlation
For two sequences $x[n]$ and $y[n]$:
$$R_{xy}[m] = \sum_{n} x[n] y[n + m]$$

### 3.2. Delay Estimation & Sign Convention
The estimated delay in samples is the peak index of the cross-correlation sequence:
$$D^* = \arg\max_{m} R_{xy}[m]$$
$$\text{delay\_ms} = \frac{D^*}{f_s} \times 1000.0$$

> **Sign Convention Invariant:**
> - $\text{delay} > 0$ means the capture lags behind the reference ($y[n]$ arrived after $x[n]$).
> - $\text{delay} < 0$ means the capture leads the reference.

### 3.3. Normalized Cross-Correlation (NCC)
Over the aligned overlap window of length $M$:
$$\text{NCC} = \frac{\sum_{n=0}^{M-1} x_{\text{aligned}}[n] y_{\text{aligned}}[n]}{\sqrt{\left(\sum_{n=0}^{M-1} x_{\text{aligned}}^2[n]\right) \left(\sum_{n=0}^{M-1} y_{\text{aligned}}^2[n]\right)}}$$
- Range: $[-1.0, +1.0]$.
- $\text{NCC} = 1.0$ indicates identical waveform shape up to a positive linear scalar multiplier.

### 3.4. Least-Squares Gain ($\hat{g}$)
Given aligned sequences under the linear model $y[n] = g \cdot x[n] + v[n]$, the optimal scalar gain $\hat{g}$ minimizing the sum of squared errors $\sum (y[n] - g x[n])^2$ is:
$$\hat{g} = \frac{\mathbf{x}^T \mathbf{y}}{\mathbf{x}^T \mathbf{x}} = \frac{\sum_{n=0}^{M-1} x_{\text{aligned}}[n] y_{\text{aligned}}[n]}{\sum_{n=0}^{M-1} x_{\text{aligned}}^2[n]}$$
*Resilient against zero-mean additive Gaussian noise; does not artificially inflate with noise like RMS gain.*

### 3.5. Root Mean Square Error (RMSE)
$$\text{RMSE} = \sqrt{\frac{1}{M} \sum_{n=0}^{M-1} \left(y_{\text{aligned}}[n] - \hat{g} \cdot x_{\text{aligned}}[n]\right)^2}$$

### 3.6. Normalized Root Mean Square Error (NRMSE)
$$\text{NRMSE} = \frac{\text{RMSE}}{\text{RMS}(x_{\text{aligned}})}$$

### 3.7. Signal-to-Error Ratio (SER, dB)
$$\text{SER (dB)} = 10 \log_{10} \left( \frac{\sum_{n=0}^{M-1} x_{\text{aligned}}^2[n]}{\sum_{n=0}^{M-1} \left(y_{\text{aligned}}[n] - \hat{g} \cdot x_{\text{aligned}}[n]\right)^2} \right)$$
*Quantifies preserved reference energy relative to unexplained residual noise/distortion energy.*

---

## 4. Spectral & Frequency-Domain Metrics

### 4.1. Discrete Fourier Transform (DFT)
$$X[k] = \sum_{n=0}^{N-1} x[n] w[n] e^{-j 2\pi k n / N}, \quad k = 0, 1, \dots, N-1$$

### 4.2. Welch Modified Periodogram Averaging
For $K$ windowed segments of length $L$ with overlap $D$:
$$\hat{P}_{xx}(f) = \frac{1}{K \cdot f_s \cdot S_2} \sum_{i=1}^K |X_i(f)|^2$$
where $S_2 = \sum_{n=0}^{L-1} w^2[n]$ is the window noise power normalization factor (Heinzel et al., R003).

### 4.3. Equivalent Noise Bandwidth (ENBW)
$$\text{ENBW} = f_s \cdot \frac{\sum_{n=0}^{L-1} w^2[n]}{\left(\sum_{n=0}^{L-1} w[n]\right)^2}$$

### 4.4. Band Energy Fraction
For a specified frequency band $[f_a, f_b]$:
$$\text{BER}_{[f_a, f_b]} = \frac{\int_{f_a}^{f_b} \hat{P}_{xx}(f) df}{\int_{0}^{f_s / 2} \hat{P}_{xx}(f) df}$$

### 4.5. Magnitude-Squared Coherence
$$\gamma_{xy}^2(f) = \frac{|P_{xy}(f)|^2}{P_{xx}(f) P_{yy}(f)}$$
- Range: $[0.0, 1.0]$.
- Measures the degree of linear causality between excitation and capture at each frequency $f$.
