# AuscultaForge — Acoustic Phantom Fabrication & Curing Log

**Document ID:** `AF-HW-LOG-PHANTOM-20261123`  
**Date of Fabrication:** 23 November 2026 (evening, operator-reported)  
**Inspection Date:** 24 November 2026 (07:20 UTC+3) & 25 November 2026 (Pre-Lab Gate)  
**Specimen Identifier:** `SPECIMEN-RTV2-20261123-01`  
**Author / Fabricator:** Operator (Team Member), Audit by Module A/C Leads

---

## 1. Material Identification & Unverified Details

- **Silicone Base (Operator-Reported):** AnkaHobiMarket RTV-2 Mold Silicone (500 g container).
  - *Unverified Details:* Exact catalyst chemistry (e.g., organotin vs. platinum), Shore hardness scale (A vs. 00), component densities, and exact manufacturer cure schedule have **not** been independently verified from a primary Technical Data Sheet (TDS).
- **Curing Agent (Catalyst):** Separate transparent catalyst bottle supplied with kit.
- **Additives:** None reported.

---

## 2. Mold Geometry & Nominal Volumetric Dosing

Due to the absence of a precision gram/milligram scale at the preparation site, volumetric portioning using standard kitchen spoons was used (operator-reported):

### 2.1 Mold Dimensions
- **Mold Vessel:** Circular flat-bottom Borcam glass dish.
- **Internal Diameter ($D$):** $12.0\text{ cm}$ (Radius $r = 6.0\text{ cm}$).
- **Nominal Base Area ($A$):** $A = \pi \cdot r^2 = \pi \cdot (6.0\text{ cm})^2 \approx 113.10\text{ cm}^2$.
- **Target Specimen Thickness ($h$):** $\approx 10.0\text{ mm}$ ($1.0\text{ cm}$) ruler estimate.
- **Nominal Target Volume ($V_{\text{target}}$):** $A \cdot h \approx 113.10\text{ mL}$.

### 2.2 Volumetric Portioning & Limitations
Assuming $1\text{ metric tablespoon (tbsp)} = 15.0\text{ mL}$ and $1\text{ metric teaspoon (tsp)} = 5.0\text{ mL}$:
1. Initial pour: $6\text{ tbsp}$ base ($\approx 90\text{ mL}$), fluid depth $\approx 7\text{ mm}$.
2. Adjustment pour: $+1\text{ tbsp}$ base ($\approx 15\text{ mL}$), bringing nominal depth to $\approx 10\text{ mm}$ ($V_{\text{base}} \approx 105.0\text{ mL}$).
3. Catalyst addition: $\approx \frac{3}{4}\text{ tsp}$ ($V_{\text{cat}} \approx 3.75\text{ mL}$).
4. **Nominal Volumetric Ratio:** $r_V = \frac{3.75}{105.0} \approx 3.57\%$.
5. **Limitation:** Because kitchen spoons vary in fill/meniscus and component densities ($\rho_{\text{base}}, \rho_{\text{cat}}$) are unverified, the true mass ratio is unknown. Mixing duration, ambient humidity, and exact cure kinetics were not instrumented.

---

## 3. Curing State & Observations

| Timestamp | Observed State (Operator-Reported) | Verdict |
|---|---|---|
| **23 Nov 2026 (evening)** | Poured and hand-stirred in Borcam dish; air bubbles visible (no vacuum degassing). | **POURED / MIXED** |
| **24 Nov 2026 07:20** | Surface remained tacky; fluid displacement observed under gentle tilt. | **CURE_NOT_VERIFIED / IN_PROGRESS** |
| **25 Nov 2026 08:30** | Mandatory pre-lab cure gate inspection at laboratory bench. | *PENDING PHYSICAL CHECK* |

---

## 4. Mandatory Cure Gate & Substitution Policy

> [!CAUTION]
> **STRICT PROHIBITION:** **DO NOT** use partially cured, tacky, or liquid RTV-2 silicone on the test bench, **even with a protective pad placed on top**. Partially cured silicone can leak uncatalyzed resin/catalyst, deform under load, and contaminate or damage the stethoscope chestpiece and MEMS microphone.

If `SPECIMEN-RTV2-20261123-01` fails the pre-lab cure gate (non-tacky, cohesive solid-elastic state):
1. Set the Borcam RTV-2 specimen aside untouched.
2. Substitute a **separate, fully cured compliant material** (e.g., dry cured elastomer/silicone pad) for exploratory bench testing.
3. Explicitly record the material substitution and its limitations in the trial `--notes`. **Never** claim validated soft-tissue equivalence for an exploratory substitute.
