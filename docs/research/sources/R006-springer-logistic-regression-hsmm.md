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
1. **Verified R006 Feature Extraction Pipeline:**
   - Raw PCG $\to$ polyphase anti-alias downsample to $1,000\text{ Hz}$ (`springer_polyphase_anti_alias_1000hz`).
   - Note on Filter Provenance: Schmidt's 25–400 Hz 4th-order Butterworth filter (R005) is kept OUT of the strict Springer profile to maintain single-source provenance.
   - Four feature envelopes extracted at $1,000\text{ Hz}$:
     - **Feature 1: Homomorphic Envelope:** Captures low-frequency pulse shape.
     - **Feature 2: Hilbert Transform Envelope:** Captures instantaneous energy peaks.
     - **Feature 3: Stationary Wavelet Transform (SWT):** Decomposes energy in the 40–128 Hz band (Level 3).
     - **Feature 4: Power Spectral Density Envelope:** Mean PSD across the **40–60 Hz** band using a $50\text{ ms}$ analysis window ($n_{\text{perseg}} = 50$ samples at $1,000\text{ Hz}$), $50\%$ overlap ($n_{\text{overlap}} = 25$ samples), and a Hamming window (`window="hamming"`). No arbitrary $N_{\text{FFT}}$ is invented.
   - Per-recording feature normalization: subtract mean / divide standard deviation ($z$-score normalization).
   - Feature vectors downsampled to **$50\text{ Hz}$** ($20\text{ ms}$ feature cadence).
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
