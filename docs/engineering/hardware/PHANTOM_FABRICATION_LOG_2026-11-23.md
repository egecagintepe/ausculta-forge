# AuscultaForge — Acoustic Phantom Fabrication & Curing Log

**Document ID:** `AF-HW-LOG-PHANTOM-20261123`  
**Date of Fabrication:** 23 November 2026 (~21:00–22:00 UTC+3)  
**Inspection Date:** 24 November 2026 (07:20 UTC+3) & 25 November 2026 (Pre-Lab Gate)  
**Specimen Identifier:** `SPECIMEN-RTV2-20261123-01`  
**Author / Fabricator:** Operator (Team Member), Audit by Module A/C Leads  

---

## 1. Material & Chemical Reagent Identification

- **Silicone Base:** AnkaHobiMarket RTV-2 Condensation-Cure Mold Silicone (500 g container).
  - *Nominal Hardness (Vendor Claim):* 5 Shore (scale A vs. 00 to be verified on physical container).
  - *Color / Appearance:* Semi-translucent liquid base.
- **Curing Agent (Catalyst):** Transparent condensation-cure organotin catalyst in separate bottle (supplied with kit).
- **Vendor-Stated Target Ratio:** ~3% (mass basis according to technical data conventions; vendor instructions on packaging must be verified).
- **Additives:** None (no water, mineral oil, thixotropic agents, or color pigments added).

---

## 2. Mold Geometry & Volumetric Fabrication Method

Due to the absence of a precision digital milligram/gram balance at the home fabrication station, volumetric portioning using standardized kitchen measures was employed:

### 2.1 Mold Dimensions
- **Mold Vessel:** Circular flat-bottom Borcam borosilicate glass dish.
- **Internal Diameter ($D$):** $12.0\text{ cm}$ (Radius $r = 6.0\text{ cm}$).
- **Nominal Base Area ($A$):** 
  $$A = \pi \cdot r^2 = \pi \cdot (6.0\text{ cm})^2 \approx 113.10\text{ cm}^2$$
- **Target Specimen Thickness ($h$):** $10.0\text{ mm}$ ($1.0\text{ cm}$) measured by ruler against mold wall.
- **Nominal Target Volume ($V_{target}$):**
  $$V_{target} = A \cdot h = 113.10\text{ cm}^2 \cdot 1.0\text{ cm} \approx 113.10\text{ cm}^3\ (113.10\text{ mL})$$

### 2.2 Dosing Sequence & Volume Approximation
Standard volume units assume $1\text{ metric tablespoon (tbsp)} = 15.0\text{ mL}$ and $1\text{ metric teaspoon (tsp)} = 5.0\text{ mL}$.

1. **Initial Base Pour:** 6 heaped tablespoons of silicone base poured into mold ($\approx 6 \times 15 = 90\text{ mL}$).
2. **Depth Check:** Fluid fill height measured $\approx 7\text{ mm}$ against ruler.
3. **Adjustment Pour:** 1 additional heaped tablespoon of base added ($\approx 15\text{ mL}$), bringing nominal liquid depth to $\approx 10\text{ mm}$.
   - **Total Estimated Base Volume ($V_{base}$):** $\approx 7\text{ tbsp} \approx 105.0\text{ mL}$.
4. **Catalyst Dosing:** Approximately $\frac{3}{4}\text{ teaspoon}$ of catalyst added directly into the mold:
   $$V_{cat} \approx 0.75 \times 5.0\text{ mL} = 3.75\text{ mL}$$
5. **Total Mixture Volume ($V_{total}$):**
   $$V_{total} = V_{base} + V_{cat} \approx 105.0 + 3.75 = 108.75\text{ mL}$$
   *(Closely matches target mold cavity requirement of $113.1\text{ mL}$ within volumetric meniscus tolerances).*

### 2.3 Ratio Analysis: Volumetric vs. Mass Ratio
The volumetric ratio achieved during preparation is:
$$r_V = \frac{V_{cat}}{V_{base}} = \frac{3.75\text{ mL}}{105.0\text{ mL}} \approx 3.57\%$$

True chemical mass ratio ($r_m$) is governed by component densities:
$$r_m = \frac{m_{cat}}{m_{base}} = \frac{\rho_{cat} \cdot V_{cat}}{\rho_{base} \cdot V_{base}} = r_V \cdot \frac{\rho_{cat}}{\rho_{base}}$$

*Illustrative Density Calculation (Pending TDS Verification):*
- If $\rho_{base} \approx 1.10\text{ g/mL}$ and $\rho_{cat} \approx 1.00\text{ g/mL}$:
  $$r_m = 3.57\% \cdot \left(\frac{1.00}{1.10}\right) \approx 3.25\%$$
- This volumetric dosing was intentional and structured, but constitutes a **nominal volumetric estimate**, not an analytically verified mass ratio.

---

## 3. Mixing, Environmental Conditions & Process Deviations

- **Mixing Method:** Hand stirred with a clean spatula directly inside the Borcam mold for ~3–4 minutes until visual consistency achieved.
- **Ambient Temperature:** $19^\circ\text{C} – 23^\circ\text{C}$ (residential room temperature).
- **Relative Humidity:** Ambient unmonitored indoor air.
- **Process Deviations / Safety Incidents:**
  - Minor droplet spill and skin contact occurred during pouring; immediately washed thoroughly with warm water and detergent per chemical hygiene protocols. No personal identifying information recorded.
  - No vacuum degassing chamber was available; small dispersed air bubbles remained suspended in the pour.

---

## 4. Curing State & In-Progress Observations

| Timestamp | Elapsed Time | Observed Physical State | Verdict |
|---|---|---|---|
| **23 Nov 2026 22:00** | $0\text{ h}$ | Freshly poured viscous liquid, transparent bubbles visible. | **POURED / MIXED** |
| **24 Nov 2026 07:20** | $\approx 9.5\text{ h}$ | Surface remains tacky; fluid displacement under gentle lateral vessel tilt. No structural set observed. | **CURE NOT VERIFIED / IN PROGRESS** |
| **24 Nov 2026 22:00** | $\approx 24\text{ h}$ | Scheduled 24-hour cure inspection prior to lab departure. | *To be recorded* |
| **25 Nov 2026 08:30** | $\approx 34.5\text{ h}$ | Pre-lab bench entry check at university laboratory. | *To be recorded* |

> [!CAUTION]
> **Chemical Handling Restrictions:**
> 1. **DO NOT** attempt to accelerate curing by microwave heating, hair dryer, or oven baking. Heat may degrade the condensation catalyst, cause rapid gas boiling, or crack the glass dish.
> 2. **DO NOT** add additional catalyst onto the surface of a partially cured/tacky specimen; unmixed catalyst will create an uneven, brittle skin while leaving the core uncured.
> 3. **DO NOT** bring an uncured, tacky, or leaking silicone mass into direct contact with the laboratory breadboard, stethoscope chestpiece diaphragm, or MEMS microphone acoustic port.

---

## 5. Physical Acceptance Criteria for 25 Nov Lab

Before specimen `SPECIMEN-RTV2-20261123-01` may be used as the acoustic medium on the test bench, it must satisfy all 5 physical criteria:

```
[ ] 1. Surface Tack: Zero surface stickiness (gloved finger leaves no residue and experiences no adhesion).
[ ] 2. Cohesive Integrity: Demolds cleanly from Borcam without tearing, liquid pockets, or slumping.
[ ] 3. Thickness Uniformity: Measured with vernier caliper at center and 4 orthogonal perimeter points:
       Center: ____ mm | North: ____ mm | South: ____ mm | East: ____ mm | West: ____ mm (Target: 10 ± 2 mm).
[ ] 4. Bubble Inclusions: No continuous bubble channels bridging top and bottom acoustic surfaces.
[ ] 5. Flatness: Rests flat against the exciter drive plate without rocking or air bridging.
```

---

## 6. Contingency Plan: Backup Fabrication & Fallback Medium

### 6.1 Precision Backup Sample Procedure (If Needed with Gram Scale)
If the primary specimen fails to cure and fresh silicone is mixed with a $0.1\text{ g}$ scale:
- Mold: $8.0\text{ cm}$ diameter circular cup ($r = 4.0\text{ cm}$, $h = 1.0\text{ cm} \rightarrow V = 50.27\text{ mL}$).
- Required Mass (at $\rho_{mix} \approx 1.10\text{ g/mL}$): $55.3\text{ g}$.
- Batch Preparation (with slight excess for mold filling):
  - **Base:** $60.0\text{ g}$ weighed into clean disposable cup.
  - **Catalyst:** $1.80\text{ g}$ ($3.00\text{ wt}\%$) added via syringe/pipette.
  - Mix for 3 minutes, scrape container walls, pour into mold, and place surplus in witness cup.

### 6.2 Pre-Lab Fallback: Exploratory Dry Compliant Pad
If silicone curing has not reached complete solid-elastic state by Wednesday morning 08:30:
- **Fallback Material:** Clean, intact, dry compliant polyurethane / neoprene elastomer pad ($10\text{ mm}$ thickness).
- **Classification:** **`EXPLORATORY BENCH ALTERNATIVE`** (NOT certified soft-tissue phantom).
- **Reporting Rule:** The trial will be executed to evaluate electrical continuity, transducer drive, and acoustic transduction; however, the formal course gate **`T-AUD-05` (Phantom S1/S2 Gate)** will remain recorded as `PARTIAL / BENCH ALTERNATIVE PENDING FORMAL SILICONE PUCK`.
