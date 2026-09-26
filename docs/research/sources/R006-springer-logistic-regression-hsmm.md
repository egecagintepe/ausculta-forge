# R006 — Springer et al. (2016): Logistic Regression-HSMM Heart Sound Segmentation

## 1. Bibliographic Reference
- **Authors:** David B. Springer, Lionel Tarassenko, Gari D. Clifford (University of Oxford / Emory University).
- **Title:** *Logistic Regression-HSMM-based Heart Sound Segmentation*.
- **Journal:** *IEEE Transactions on Biomedical Engineering*, Vol. 63, No. 4, April 2016, pp. 742–752.
- **DOI:** 10.1109/TBME.2015.2475278.
- **Authority Level:** **PRIMARY TARGET MODEL FOR PCG SEGMENTATION**.

---

## 2. Scope & Application to AuscultaForge
R006 is the authoritative modern reference for automated PCG cycle segmentation, extending Schmidt et al. (R005) with multi-feature fusion and discriminative logistic regression emission modeling.

### Key Architectural Components:
1. **Multi-Rate Downsampling Pipeline:**
   - Audio input downsampled to $1,000\text{ Hz}$ with anti-aliasing.
   - Filtered with a 4th-order Butterworth bandpass ($25\text{--}400\text{ Hz}$).
   - Four complementary envelope features extracted and decimated to **$50\text{ Hz}$** ($20\text{ ms}$ feature cadence):
     - **Feature 1: Homomorphic Envelope:** Captures low-frequency pulse shape.
     - **Feature 2: Hilbert Transform Envelope:** Captures instantaneous energy peaks.
     - **Feature 3: Stationary Wavelet Transform (SWT):** Decomposes energy in the 40–128 Hz band (Level 3).
     - **Feature 4: Power Spectral Density Envelope:** Short-time Fourier energy in the 40–50 Hz subband.
2. **Logistic Regression Emission Probabilities:**
   - Replaces traditional generative Gaussian Mixture Models (GMMs) with multinomial logistic regression, directly estimating state posterior probabilities:
     $$P(q_t = j \mid \mathbf{o}_t) = \frac{\exp(\mathbf{w}_j^T \mathbf{o}_t)}{\sum_{k=1}^4 \exp(\mathbf{w}_k^T \mathbf{o}_t)}$$
3. **Explicit State Duration Modeling (HSMM):**
   - Gaussian duration distributions $p_j(d)$ for $S_1$, systole, $S_2$, and diastole derived from heart rate statistics.
4. **Modified Viterbi Algorithm:**
   - Jointly optimizes state sequence and state duration path:
     $$\delta_t(j, d) = \max_{i \ne j} \left[ \max_{d'} \delta_{t-d}(i, d') a_{ij} \right] p_j(d) \prod_{s=t-d+1}^t b_j(\mathbf{o}_s)$$

---

## 3. Implementation Staging in AuscultaForge
- **Stage A (Scheduled `NEXT_DSP`):** Implement the four deterministic feature extractors at $50\text{ Hz}$ (`PCG_EVENT_FEATURES_V1`) without machine learning.
- **Stage B (Scheduled `RESEARCH_LATER`):** Implement the logistic regression weights and modified Viterbi sequence decoder (`SPRINGER_SEGMENTATION_RESEARCH_V1`).
