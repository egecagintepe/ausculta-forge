# AuscultaForge — Spectral Analysis, Welch PSD & Time-Frequency Methods
**Document ID:** `AF-SCI-SPECTRAL-V01`  
**Classification:** `CODE_VERIFIED` / `TEST_VERIFIED`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Reference File:** `software/pcg_core/scientific/spectral.py`  
**Associated Tests:** `software/tests/test_scientific_spectral.py`

---

## 1. Discrete Fourier Transform & Spectral Leakage

The Discrete Fourier Transform (DFT) transforms a finite sequence of $N$ time-domain samples $x[n]$ into $N$ complex frequency-domain bins $X[k]$:
$$X[k] = \sum_{n=0}^{N-1} x[n] e^{-j \frac{2\pi}{N} k n}, \quad k = 0, 1, \dots, N-1$$
Each bin index $k$ corresponds to the continuous physical frequency:
$$f_k = k \frac{f_s}{N} = k \Delta f$$
where $\Delta f = f_s / N$ is the **frequency bin resolution**.

### 1.1 The Spectral Leakage Phenomenon
* Truncating a signal to a finite block of length $N$ is mathematically equivalent to multiplying an infinite signal $x_\infty[n]$ by a rectangular window $w_R[n]$.
* In the frequency domain, multiplication becomes convolution:
  $$X_R(e^{j\omega}) = \frac{1}{2\pi} X_\infty(e^{j\omega}) * W_R(e^{j\omega})$$
* The Fourier transform of a rectangular window is a Dirichlet kernel (periodic sinc function):
  $$W_R(e^{j\omega}) = e^{-j \omega \frac{N-1}{2}} \frac{\sin(\omega N / 2)}{\sin(\omega / 2)}$$
* The side-lobes of the Dirichlet kernel decay slowly (first side-lobe is only $-13.3 \text{ dB}$ below the main lobe). If an acoustic frequency component does not land exactly on a bin center, its energy leaks across the entire spectrum.

### 1.2 Window Function Selection
To suppress spectral leakage, AuscultaForge applies tapered window functions:

| Window Type | Main Lobe Width ($-3 \text{ dB}$) | First Sidelobe Level | Sidelobe Roll-off Rate | AuscultaForge Role |
|---|---|---|---|---|
| **Rectangular** | $0.89 \Delta f$ | $-13.3 \text{ dB}$ | $-6 \text{ dB/octave}$ | Transient testing (virtual bench impulse). |
| **Hann (Hanning)** | $1.44 \Delta f$ | **$-31.5 \text{ dB}$** | **$-18 \text{ dB/octave}$** | **Primary Baseline for Welch PSD & STFT.** |
| **Hamming** | $1.30 \Delta f$ | $-42.7 \text{ dB}$ | $-6 \text{ dB/octave}$ | General voice / acoustic processing. |
| **Blackman-Harris** | $1.92 \Delta f$ | $-92.0 \text{ dB}$ | $-18 \text{ dB/octave}$ | High-dynamic-range harmonic distortion tests. |

* The **Hann Window** is adopted as the primary scientific standard:
  $$w_{\text{hann}}[n] = 0.5 \left( 1 - \cos\left( \frac{2\pi n}{N-1} \right) \right), \quad 0 \le n \le N-1$$
  Its rapid $-18 \text{ dB/octave}$ sidelobe decay ensures that high-amplitude low-frequency heart sounds ($S_1, S_2$) do not leak into and mask faint high-frequency systolic murmurs ($> 200 \text{ Hz}$).

---

## 2. Welch Power Spectral Density (PSD) Estimation

A single periodogram computed from an $N$-point FFT exhibits high statistical variance: as $N \to \infty$, the periodogram variance does not converge to zero.

### 2.1 The Welch Method Formulation
To obtain a consistent, low-variance estimate of the Power Spectral Density $S_{xx}(f)$, AuscultaForge implements the **Welch Method** (`scipy.signal.welch`):
1. **Partitioning:** The record of length $L$ is divided into $K$ overlapping segments of length $M$, with overlap $D = M / 2$ ($50\%$ overlap):
   $$x_i[n] = x[n + i(M - D)], \quad 0 \le n \le M-1, \quad i = 0, \dots, K-1$$
2. **Windowing & Periodogram:** Each segment is multiplied by a Hann window $w[n]$ and transformed via FFT:
   $$P_i(f) = \frac{1}{U \cdot M} \left| \sum_{n=0}^{M-1} x_i[n] w[n] e^{-j 2\pi f n / f_s} \right|^2$$
   where $U$ is the window power normalization factor:
   $$U = \frac{1}{M} \sum_{n=0}^{M-1} w^2[n]$$
3. **Ensemble Averaging:** The final Welch PSD estimate is the average across all $K$ modified periodograms:
   $$\hat{S}_{xx}(f) = \frac{1}{K} \sum_{i=0}^{K-1} P_i(f)$$

### 2.2 Variance Reduction & Resolution Trade-off
* **Variance Reduction:** Averaging $K$ independent segments reduces the variance of the spectral estimate by a factor of approximately $K$:
  $$\text{Var}\{\hat{S}_{xx}(f)\} \approx \frac{1}{K} S_{xx}^2(f)$$
* **Resolution Trade-off (Gabor / Uncertainty Limit):**
  $$\Delta t \cdot \Delta f \ge \frac{1}{4\pi}$$
  Increasing segment length $M$ improves frequency resolution ($\Delta f = f_s / M$), but reduces the number of segments $K$ for a fixed record duration, increasing estimate variance.

### 2.3 AuscultaForge Standard PSD Configuration
In `software/pcg_core/scientific/spectral.py`:
* **Sampling Rate ($f_s$):** $48,000 \text{ Hz}$
* **Segment Length ($N_{\text{FFT}}$):** $4,096 \text{ samples}$
* **Segment Duration:** $\tau_{\text{seg}} = 4096 / 48000 \approx 85.33 \text{ ms}$
* **Frequency Bin Spacing:**
  $$\Delta f = \frac{48,000 \text{ Hz}}{4,096} = 11.71875 \text{ Hz}$$
* **Overlap:** $50\%$ ($2,048 \text{ samples} \approx 42.67 \text{ ms}$).

---

## 3. High-Resolution Mains Interference Quantification

Power mains interference (50 Hz electrical pickup from ambient power lines, light fixtures, and unshielded cables) is one of the six mandatory advisor characterization measurements.

### 3.1 Spectral Peak Extraction Algorithm
Rather than relying on broad bandpass averages, `pcg_core.scientific.spectral.analyze_mains_interference()` performs narrow spectral extraction around the fundamental and its exact integer harmonics:
* **Fundamental:** $f_1 = 50.0 \text{ Hz}$
* **Harmonic Series:** $f_k = k \times 50.0 \text{ Hz} \ (100, 150, 200, 250, 300 \text{ Hz})$

For each harmonic $f_k$:
1. A narrow integration window of bandwidth $B = \pm 2.5 \text{ Hz}$ is evaluated around $f_k$:
   $$P_{\text{mains}}(f_k) = \int_{f_k - 2.5}^{f_k + 2.5} \hat{S}_{xx}(f) df$$
2. The local baseline acoustic floor $P_{\text{floor}}(f_k)$ is estimated from adjacent shoulder bands:
   $$[f_k - 7.5, f_k - 2.5] \cup [f_k + 2.5, f_k + 7.5]$$
3. The **Mains-to-Background Ratio (MBR)** in relative dB:
   $$\text{MBR}(f_k) = 10 \log_{10} \left( \frac{P_{\text{mains}}(f_k)}{P_{\text{floor}}(f_k)} \right)$$

* **Advisor Acceptance Threshold:** Under proper grounding and shielding, $\text{MBR}(50\text{ Hz})$ must remain below $+15 \text{ dB}$ above the quiescent floor during bench characterization.
