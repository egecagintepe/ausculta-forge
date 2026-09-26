# R008 — Rangayyan (2005): Biomedical Image Analysis

## 1. Bibliographic Reference
- **Author:** Rangaraj M. Rangayyan, Ph.D., FIEEE, FAIMBE.
- **Title:** *Biomedical Image Analysis*.
- **Publisher:** CRC Press, Boca Raton, Florida.
- **Year:** 2005.
- **ISBN:** 978-0-8493-9698-4.
- **Authority Level:** **LOW DIRECT RELEVANCE — BACKGROUND ARCHIVE ONLY**.

---

## 2. Explicit Assessment of Relevance
R008 is cataloged in the AuscultaForge research registry to document laboratory literature assets, but it is explicitly designated as **LOW DIRECT RELEVANCE** for the current one-dimensional acoustic and phonocardiographic signal processing pipeline.

### Why R008 Is Not Applicable to AuscultaForge Core:
1. **Dimensionality Mismatch:**
   - R008 addresses two-dimensional spatial image processing ($I(x, y)$), spatial convolutions, radiographic contrast enhancement, and 2D morphological operators (dilation, erosion, opening, closing).
   - AuscultaForge processes one-dimensional discrete acoustic time-series ($x[n]$) and linear time-invariant 1D filtering.
2. **Spectrogram Misconception:**
   - While time-frequency representations (STFT spectrograms) can be rendered as 2D visual arrays, treating an acoustic spectrogram as a 2D digital image for spatial image filtering without physical acoustic constraints violates the uncertainty principle ($\Delta t \cdot \Delta f \ge 1 / 4\pi$) and introduces phase inconsistencies.
3. **Project Policy:**
   - 2D computer vision algorithms from R008 will **NOT** be imported into AuscultaForge DSP. All PCG analysis remains strictly grounded in 1D time-frequency DSP theory (R001–R007).
