# AuscultaForge — Research Backlog & Open Metrology Gaps

The following topics represent active research gaps. In accordance with the AuscultaForge Scientific Development Rule, **no software implementation shall occur for these topics until rigorous literature grounding and formal mathematical modeling are completed**.

---

## 1. Open Research Gaps

| Research Gap ID | Topic | Missing Theoretical Prerequisite | Required Literature Grounding | Status |
|---|---|---|---|---|
| **GAP-01** | Chestpiece Cavity Acoustic Model | Lumped-element acoustic impedance network ($M_a, C_a, R_a$) for bell vs. diaphragm chamber. | Kinsler et al., *Fundamentals of Acoustics*; Beranek, *Acoustics*. | `RESEARCH_LATER` |
| **GAP-02** | Phantom Viscoelastic Propagation Model | Wave speed ($c$) and frequency-dependent attenuation ($\alpha(f) = \alpha_0 f^\eta$) in silicone/gel. | Duck, *Physical Properties of Tissue*; Cobbold, *Foundations of Biomedical Ultrasound*. | `RESEARCH_LATER` |
| **GAP-03** | Calibrated SPL Conversion | Transducer voltage/digital code mapping to absolute acoustic pressure ($p\text{ in Pa}$). | IEC 60651 / IEC 61672 Sound Level Meter Standards. | `RESEARCH_LATER` |
| **GAP-04** | $H_1$ and $H_2$ Transfer Function Estimators | Formal random excitation design and cross-spectral averaging with input/output noise separation. | Bendat & Piersol, *Random Data: Analysis and Measurement Procedures* (4th Ed. 2010). | `RESEARCH_LATER` |
| **GAP-05** | Transfer Function Uncertainty Bounds | Variance and confidence intervals for non-parametric frequency response function estimates. | Bendat & Piersol (2010, Ch. 6); ISO/IEC Guide 98-3 (GUM). | `RESEARCH_LATER` |
| **GAP-06** | Metrology Uncertainty Budget | Complete Type A (statistical) and Type B (systematic) uncertainty budget for phantom validation. | JCGM 100:2008 (GUM Guide to the Expression of Uncertainty in Measurement). | `RESEARCH_LATER` |
| **GAP-07** | Sensor Re-positioning Repeatability (Gauge R&R) | Statistical protocol for evaluating sensor placement, contact force variation, and coupling repeatability. | Montgomery, *Design and Analysis of Experiments*; AIAG Measurement Systems Analysis. | `RESEARCH_LATER` |
| **GAP-08** | Digital MEMS Calibration Methodology | Electrical-to-acoustic calibration methodology without analog test points on the I2S MEMS PCB. | PUI Audio Application Notes; IEEE 269 Standard for Acoustic Measurements. | `RESEARCH_LATER` |
| **GAP-09** | Bit-Exact Integer Raw Archival | Storage pipeline to record and archive unadulterated integer PCM words (24-bit in 32-bit slot) directly from I2S hardware without host float32 normalization. | Audio engineering data preservation standards (AES31-3 / EBU BWF). | `RESEARCH_LATER` |

---


## 2. Topic Details & Research Directions

### GAP-01: Chestpiece Cavity Acoustic Model
- **Scientific Challenge:** The entrapped air column inside the stethoscope chestpiece acts as an acoustic resonator with compliance $C = V / (\rho c^2)$ and acoustic inertance $M = \rho l / A$.
- **Why Deferred:** Simple digital filtering cannot model this acoustic cavity without measuring the physical physical chamber dimensions, port geometry, and diaphragm tension.
- **Rule:** Do not hard-code an assumed cavity transfer function.

### GAP-04: Frequency Response Function Estimators ($H_1, H_2$)
- **Scientific Challenge:** Estimating the true transfer function $H(f)$ under presence of noise at both input and output:
  $$H_1(f) = \frac{S_{xy}(f)}{S_{xx}(f)}, \quad H_2(f) = \frac{S_{yy}(f)}{S_{yx}(f)}$$
  Geometric mean $H_v(f) = \sqrt{H_1(f) H_2(f)}$.
- **Why Deferred:** Valid calculation requires stationary white-noise or chirp excitation with multiple synchronized trials and coherence thresholding ($\gamma^2(f) > 0.8$). It cannot be run on arbitrary uncoordinated PCG audio without producing severe spectral division artifacts.

### GAP-06: Measurement Uncertainty Budget (GUM)
- **Scientific Challenge:** Any reported acoustic transmission loss or gain must be accompanied by an expanded uncertainty interval $U = k \cdot u_c$ ($k=2$ for 95% confidence).
- **Why Deferred:** Requires quantifying DAC quantization uncertainty, amplifier thermal drift, phantom temperature coefficient, MEMS sensitivity drift, and digital round-off error.
