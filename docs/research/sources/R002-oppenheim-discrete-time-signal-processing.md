# R002 — Oppenheim & Schafer (2010): Discrete-Time Signal Processing

## 1. Bibliographic Reference
- **Authors:** Alan V. Oppenheim (MIT), Ronald W. Schafer (Stanford / HP Labs).
- **Title:** *Discrete-Time Signal Processing*.
- **Edition:** Third Edition (2010).
- **Publisher:** Pearson Higher Education.
- **ISBN:** 978-0-13-198842-2.
- **Authority Level:** **CANONICAL MATHEMATICAL DSP REFERENCE**.

---

## 2. Scope & Application to AuscultaForge
R002 provides the foundational discrete-time mathematics for all digital filtering, multirate resampling, quantization models, and spectral transforms in `pcg_core`.

### Key Chapter References:
- **Chapter 2: Discrete-Time Signals and Systems:** Linearity, time-invariance, convolution sum, stability criteria, and difference equations.
- **Chapter 4: Sampling of Continuous-Time Signals:** Nyquist-Shannon sampling theorem, continuous-to-discrete conversion, aliasing mechanisms, and multirate decimation/interpolation.
- **Chapter 5: Transform Analysis of Linear Time-Invariant Systems:** Frequency response magnitude, unwrapped phase response, group delay $\tau_g(\omega) = -d\arg[H(e^{j\omega})]/d\omega$, and minimum-phase vs. linear-phase systems.
- **Chapter 7: Filter Design Techniques:** Bilinear transformation for analog-to-digital IIR filter synthesis; Butterworth prototype polynomial factorization.
- **Chapter 8 & 9: The Discrete Fourier Transform & Computation:** DFT properties, zero-padding, Fast Fourier Transform (FFT) circular vs. linear convolution.
- **Chapter 11: Parametric and Nonparametric Signal Modeling:** Autocorrelation, cross-correlation, and linear system identification.
- **Chapter 12: Hilbert Transform and Analytic Signals:** Discrete Hilbert transform, Kramers-Kronig relations, and complex analytic signal representation for envelope extraction.

---

## 3. Key Theoretical Takeaways for AuscultaForge
1. **Sampling & Nyquist Protection:**
   - Demonstrates why changing sample rates requires strict anti-aliasing low-pass filtering. AuscultaForge uses `scipy.signal.resample_poly` with a Kaiser-windowed sinc filter rather than naive decimation (`samples[::N]`).
2. **Phase Distortion in Causal IIR Filters:**
   - Demonstrates that while Butterworth filters offer maximally flat passband magnitude response, their group delay $\tau_g(\omega)$ is non-constant. Causal real-time filtering (`StreamingBandpass`) will introduce slight time dispersals across frequency, which must be accounted for during temporal alignment.
3. **Discrete Cross-Correlation & Delay:**
   - Establishes the discrete cross-correlation $R_{xy}[k] = \sum_n x[n] y[n+k]$ as the optimal linear delay estimator under additive uncorrelated Gaussian noise.
