# R007 — Liu et al. (2016): Open-Access Database & Segmentation Evaluation

## 1. Bibliographic Reference
- **Authors:** Chengyu Liu, David B. Springer, Qiao Li, Benjamin Moody, et al.
- **Title:** *An open access database for the evaluation of heart sound algorithms*.
- **Journal:** *Physiological Measurement*, Vol. 37, No. 12, December 2016, pp. 2181–2213.
- **DOI:** 10.1088/0967-3334/37/12/2181.
- **Authority Level:** **VALIDATION & BENCHMARKING AUTHORITY FOR PCG ALGORITHMS**.

---

## 2. Scope & Application to AuscultaForge
R007 establishes the formal international benchmarking protocol for evaluating heart sound segmentation and quality assessment algorithms.

### Key Evaluation Standards:
1. **Multi-Database Corpus Heterogeneity:**
   - Demonstrates that algorithms trained on a single quiet clinic database experience severe performance degradation when deployed on noisy real-world recordings.
   - Emphasizes the need for distinct training, validation, and independent test splits grouped by **subject / recording session**, not random sample splitting.
2. **Tolerance Window Event Matching:**
   - Evaluates detected $S_1$ and $S_2$ event locations against reference annotations using strict symmetric temporal tolerance windows:
     - Strict Tolerance: $\pm 60\text{ ms}$ around reference event center.
     - Clinical Tolerance: $\pm 100\text{ ms}$ around reference event center.
3. **Formal Statistical Scoring Metrics:**
   - **True Positive ($TP$):** A detected event falling within the tolerance window of an unmatched reference event.
   - **False Positive ($FP$):** A detected event with no corresponding reference event within the window.
   - **False Negative ($FN$):** A reference event with no detected event within the window.
   - **Sensitivity ($Se$):**
     $$Se = \frac{TP}{TP + FN}$$
   - **Positive Predictive Value ($PPV$ / Precision):**
     $$PPV = \frac{TP}{TP + FP}$$
   - **Harmonic Mean Score ($F_1$):**
     $$F_1 = \frac{2 \cdot Se \cdot PPV}{Se + PPV}$$

---

## 3. Project Application in Stage C Roadmap
When AuscultaForge implements Stage C segmentation evaluation on PhysioNet specimens:
- Evaluation will strictly adhere to the $\pm 60\text{ ms}$ and $\pm 100\text{ ms}$ tolerance windows.
- Results will be reported as $(Se, PPV, F_1)$ per database split, preventing inflated accuracy claims.
