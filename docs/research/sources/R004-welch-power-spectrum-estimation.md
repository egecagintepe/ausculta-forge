# R004 — Welch (1967): Averaged Modified Periodograms

## 1. Bibliographic Reference
- **Author:** Peter D. Welch (IBM Thomas J. Watson Research Center).
- **Title:** *The Use of Fast Fourier Transform for the Estimation of Power Spectra: A Method Based on Time Averaging Over Short, Modified Periodograms*.
- **Journal:** *IEEE Transactions on Audio and Electroacoustics*, Vol. AU-15, No. 2, June 1967, pp. 70–73.
- **DOI:** 10.1109/TAU.1967.1161901.
- **Authority Level:** **METHOD CANON FOR POWER SPECTRAL ESTIMATION**.

---

## 2. Scope & Application to AuscultaForge
R004 is the primary algorithm paper for non-parametric power spectral density estimation used in `pcg_core.streaming.compute_spectral_frame`, `pcg_core.analysis`, and the Session Analysis Workbench.

### Key Theoretical Elements:
1. **Division of Sequences:**
   A discrete sequence of $N$ samples is partitioned into $K$ segments of length $L$, with consecutive segments shifted by $D$ samples ($D \le L$, overlap $L - D$).
2. **Modified Periodogram:**
   Each segment $x_i[n]$ ($i = 1, \dots, K$) is multiplied by a data window $w[n]$ ($n = 0, \dots, L-1$):
   $$A_i[k] = \frac{1}{L} \sum_{n=0}^{L-1} x_i[n] w[n] e^{-j 2\pi k n / L}$$
   $$I_i(f_k) = \frac{L}{S_2} |A_i[k]|^2$$
3. **Periodogram Averaging:**
   The Welch spectral estimate is the statistical average across all $K$ modified periodograms:
   $$\hat{P}_{xx}(f_k) = \frac{1}{K} \sum_{i=1}^K I_i(f_k)$$
4. **Variance Reduction:**
   For zero overlap, the variance of the estimate is reduced by a factor of $1/K$:
   $$\text{Var}\{\hat{P}_{xx}(f)\} \approx \frac{1}{K} P_{xx}^2(f)$$
   Overlapping by 50% ($D = L/2$) recovers near-optimal variance reduction while compensating for window edge taper.

---

## 3. Trade-offs & AuscultaForge Parameters
- **Resolution vs. Variance Trade-off:**
  - Longer segment length $L \implies$ finer frequency resolution $\Delta f = f_s / L$, but fewer segments $K$ (higher variance/noise in the plot).
  - Shorter segment length $L \implies$ smoother curve (lower variance), but wider frequency bins $\Delta f$ (blurring close cardiac peaks).
- **AuscultaForge Standard Tuning:**
  - For $f_s = 4000\text{ Hz}$ offline analysis: $L = 512$ samples ($128\text{ ms}$, $\Delta f = 7.81\text{ Hz}$), $50\%$ overlap ($D = 256$), Hann window.
  - For $f_s = 48000\text{ Hz}$ raw acquisition analysis: $L = 2048$ samples ($42.67\text{ ms}$, $\Delta f = 23.44\text{ Hz}$).
