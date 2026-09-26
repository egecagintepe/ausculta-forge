# R001 — Rangayyan (2002 / 2015): Biomedical Signal Analysis

## 1. Bibliographic Reference
- **Author:** Rangaraj M. Rangayyan, Ph.D., FIEEE, FAIMBE.
- **Title:** *Biomedical Signal Analysis: A Case-Study Approach*.
- **Edition:** First Edition (2002), Second Edition (2015).
- **Publisher:** IEEE Press / John Wiley & Sons, Inc., Hoboken, New Jersey.
- **ISBN:** 978-0-470-91139-6 (2nd Ed.).
- **Authority Level:** **FOUNDATIONAL BIOMEDICAL PCG REFERENCE**.

---

## 2. Scope & Physical Application to AuscultaForge
R001 serves as the primary scientific authority for phonocardiographic signal morphology, acoustic origin of heart sounds, and clinical frequency bands.

### Key Chapter References:
- **Chapter 1: The Nature of Biomedical Signals:** Phonocardiogram generation, heart valve closure mechanics, and acoustic auscultation landmarks ($S_1$, $S_2$, $S_3$, $S_4$, murmurs).
- **Chapter 3: Filtering for Removal of Artifacts:** Baseline wander (<20 Hz), muscle contraction artifacts, acoustic ambient noise, and Butterworth bandpass filtering.
- **Chapter 4: Event Detection & Characterization:** Detection of $S_1$ and $S_2$ using energy envelopes, zero-crossing rates, and duration constraints.
- **Chapter 6: Frequency-Domain Characterization:** Power spectral density of PCG signals, dominant frequency identification, and spectral energy fraction ratios across physiological bands.

---

## 3. Key Theoretical Takeaways for AuscultaForge
1. **Cardiac Sound Acoustics:**
   - $S_1$ (first heart sound): Associated with closure of mitral and tricuspid valves; dominant energy concentrated in $20\text{--}150\text{ Hz}$.
   - $S_2$ (second heart sound): Associated with closure of aortic and pulmonary valves; higher frequency content, typically $50\text{--}250\text{ Hz}$.
   - Heart murmurs: Turbulent blood flow; high-frequency acoustic components extending up to $600\text{ Hz}$ or higher.
2. **Bandpass Filtering Policy:**
   - Literature supports PCG filtering and frequency-domain characterization; the AuscultaForge $20\text{--}600\text{ Hz}$ passband (`GENERAL_PCG_V1`) is a provisional engineering development preset that attenuates content outside the development passband (it does not "eliminate" noise). It is NOT a universal medical standard.
3. **Spectral Ratios & Partitions:**
   - Motivates the 4-band engineering spectral energy partition used in the Session Analysis Workbench:
     - $0\text{--}20\text{ Hz}$: Very-low-frequency (VLF) region; may contain sensor DC drift and motion/contact artifacts, AND potentially legitimate mechanical/acoustic cardiac content.
     - $20\text{--}150\text{ Hz}$: Fundamental cardiac acoustic energy ($S_1, S_2$).
     - $150\text{--}600\text{ Hz}$: Extended cardiac acoustic band (higher frequency heart sounds, murmurs, clicks).
     - $>600\text{ Hz}$: Extended/high-frequency acoustic content (not automatically noise).
   - These partitions are purely descriptive engineering metrics, not direct pathology or diagnostic indicators.
