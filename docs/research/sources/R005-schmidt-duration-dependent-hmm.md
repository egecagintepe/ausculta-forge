# R005 — Schmidt et al. (2010): Duration-Dependent Hidden Markov Model

## 1. Bibliographic Reference
- **Authors:** Samuel E. Schmidt, Carsten Holst-Hansen, Claus Graff, Egon Toft, Johannes J. Struijk (Aalborg University, Denmark).
- **Title:** *Segmentation of heart sound recordings by a duration-dependent hidden Markov model*.
- **Journal:** *Physiological Measurement*, Vol. 31, No. 4, April 2010, pp. 513–529.
- **DOI:** 10.1088/0967-3334/31/4/004.
- **Authority Level:** **BASELINE FOR FOUR-STATE PCG SEGMENTATION**.

---

## 2. Scope & Application to AuscultaForge
R005 establishes the standard physiological four-state hidden Markov model for segmenting phonocardiographic recordings into cardiac cycle intervals.

### Key Algorithmic Structure:
1. **Four-State Physiological Topology:**
   The heart sound cycle is modeled as an invariant cyclical sequence of four states:
   $$S_1 \longrightarrow \text{Systole} \longrightarrow S_2 \longrightarrow \text{Diastole} \longrightarrow S_1$$
2. **Preprocessing Filter Specification:**
   - Raw recordings sampled at $4,000\text{ Hz}$.
   - Bandpass filter: 4th-order zero-phase Butterworth filter with cutoffs at **$25\text{ Hz}$ and $400\text{ Hz}$**.
   - Normalization: Demeaned and scaled to unit variance.
3. **Homomorphic Envelope Extraction:**
   - Evaluates the complex cepstrum log-envelope to suppress rapid acoustic carrier oscillations and highlight mechanical event pulses:
     $$\hat{x}[n] = \exp\left( \text{LPF}\left\{ \log\left( |x[n]| + \epsilon \right) \right\} \right)$$
4. **State Duration Distributions:**
   - Models the physical durations of $S_1$, systole, $S_2$, and diastole as explicit probability density functions (Gaussian distributions), accounting for heart rate dependence (systole remains relatively fixed; diastole shortens at higher heart rates).

---

## 3. Roadmap Role in AuscultaForge
- **Stage A Roadmap:** Provides the exact filter parameters ($25\text{--}400\text{ Hz}$) and homomorphic envelope algorithm used in `PCG_EVENT_FEATURES_V1`.
- **Stage B Roadmap:** Serves as the conceptual precursor to the Logistic Regression-HSMM model of Springer et al. (R006).
