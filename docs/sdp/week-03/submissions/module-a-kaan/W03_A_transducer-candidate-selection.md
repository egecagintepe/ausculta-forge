# W03 Module A: Transducer Candidate Selection

**Week:** 3
**Module:** A
**Owner:** Kaan
**Status:** Candidate-selection research documented; procurement conditions and phantom decisions OPEN

**Closeout recorded:** 11 October 2026

This work is a student project and makes no diagnostic claim. Physical evaluation is planned on the phantom only; no human recordings are included.

## Objective

Study electret condenser (ECM) and MEMS microphones and select two candidates for comparison, as required by the Week-3 Module A plan. Record technical evidence, unresolved low-frequency requirements and phantom proposals for the Week-4 requirements freeze and Group-A purchase review.

## Inputs / Dependencies

- The advisor's SDP4 weekly plan, component requirements and student assessment criteria.
- My existing [Week-3 candidate-selection report](W03_A_candidate-selection-report_v01.pdf), preserved unchanged as evidence.
- The team's [REV01 procurement/BOM draft](../../../week-02/submissions/module-b-ozan/W02_B_procurement-bom-test_REV01.xlsx), a source of proposals, not evidence of orders or final approval.
- Ozan: department stock, current sourcing, MCU/ADC path, I2S and power compatibility. Ege: playback and recording metadata for reproducible comparisons. Their board, transport and sample-format decisions are not made by this report.

## Work Performed

### 1) Comparison pair

| Role | Candidate selected in my Week-3 report | Rationale and boundary |
|---|---|---|
| ECM | **Kingstate KECG2740PBJ** | Analogue electret candidate for evaluating the bias, analogue front end and mounting chain. **NOT the final system transducer.** |
| MEMS | **PUI DMM-4026-B-I2S-R** | I2S microphone candidate for comparison with the analogue chain. |
| MEMS bench hardware | **DMM-4026-B-I2S-EB-R** | Evaluation board carrying the selected sensor, for practical bench wiring. Sensor and board have different order codes. |

These selections define the experimental pair. They do not establish measured suitability, purchase approval or a final sensor winner. Final selection requires comparison under the same phantom conditions.

### 2) Electret versus MEMS criteria and datasheet findings

| Criterion | Kingstate ECM | PUI MEMS | Consequence |
|---|---|---|---|
| Low-frequency response | Listed 20 Hz-20 kHz; response plot starts around 50 Hz. | Listed 20 Hz-20 kHz; typical plot extends to 20 Hz. | Neither a listed range nor a typical curve guarantees tolerance in the critical 20-50 Hz region. |
| Lower -3 dB point | Not explicitly specified. The -3 dB entry for supply changing from 2 V to 1.5 V is a sensitivity change, not the cutoff. | Not explicitly specified with a guaranteed tolerance. | **OPEN for both:** obtain manufacturer evidence before approving an order, or resolve the evidence gap with the advisor. |
| Sensitivity | -40 +/-3 dB re 1 V/Pa at 1 kHz; nominal 10 mV/Pa. | -26 +/-1 dB stated, but the reference label needs clarification for digital output. | Retain reference conditions; do not compare V/Pa directly with digital full scale or silently relabel the PUI value as dBFS. |
| Noise | Datasheet SNR 56 dB(A). | Datasheet SNR 64 dB(A). | Manufacturer SNR is not our measured noise floor. A-weighting does not establish low-frequency in-band noise. |
| Supply/interface | Analogue; reviewed test conditions use 2 V and a 2.2 kohm load. Needs bias, gain, coupling/filter design and ADC. | Sensor supply 1.5-3.6 V; I2S. Confirm board wiring, logic levels, clocks and data alignment with Module B. | Compare complete acquisition chains. |
| Package/mounting | Approximately 6 mm diameter by 2.7 mm high capsule. | MEMS sensor on the proposed evaluation board. | Keep ports clear; control cavity/seal, placement, contact pressure and cable strain. |

The PUI documentation also has differing clock limits: one table specifies 2.048-4.096 MHz, while the timing section lists a higher maximum. A proposed 48 kHz, two-slot, 32-bit I2S configuration gives 3.072 MHz and fits the narrower range. This is a proposal, not a frozen or tested team configuration. Module B must handle the stated 24-bit data field, 18-bit precision and 32-bit word explicitly.

INMP441 was screened in the report. Its stated flat-response region beginning at 60 Hz does not establish the required low-frequency performance, so availability alone was insufficient to substitute it for PUI.

### 3) Phantom proposals carried from REV01

| Decision | Concrete proposal | Unresolved conditions |
|---|---|---|
| DW03-04 exciter | Motorobit 30 mm, 12 ohm vibration/resonance speaker | Exact power/electrical specifications, amplifier match, mounting and usable low-frequency output. Flat 20-500 Hz response is not established. |
| DW03-05 amplifier | PAM8403 mini amplifier module | Exact module schematic, supply/load conditions, input-coupling response and headroom. An advertised 2 x 3 W rating is not guaranteed into 12 ohms. |
| DW03-06 coupling | Transparent silicone sheet, nominal 3 mm starting thickness | Hardness, contact area, compression and effective thickness. REV01's large sheet size is a supplier form, not a confirmed quantity requirement. |
| DW03-07 rigid frame | Nominal 3 mm acrylic stock, 20 x 30 cm starting sheet, with a chestpiece clamp | Frame geometry/stiffness, fixing method and clamp pressure. Sheet size alone does not define a rigid fixture. |

All four remain **OPEN proposals**. The fixture needs recorded exciter/chestpiece positions, cable restraint, port clearance and repeatable removal/reseating. Silicone/gel coupling requires documented thickness and contact conditions. No completed construction or measured repeatability is claimed.

## Evidence

The attached PDF preserves the existing Week-3 report. This Markdown adds explicit decision status, REV01 phantom proposals and the Week-4 handoff; it does not represent a new experiment.

Manufacturer references underlying the report:

1. [Kingstate KECG2740PBJ datasheet](https://www.farnell.com/datasheets/50039.pdf).
2. [PUI DMM-4026-B-I2S-R datasheet](https://api.puiaudio.com/filename/DMM-4026-B-I2S-R.pdf).
3. [PUI evaluation-board product page](https://puiaudio.com/product/microphones/DMM-4026-B-I2S-EB-R) and [board datasheet](https://www.mouser.com/datasheet/2/334/DMM-4026-B-I2S-EB-R-1853413.pdf).
4. [TDK/InvenSense INMP441 datasheet](https://invensense.tdk.com/wp-content/uploads/2015/02/INMP441.pdf), screened alternative.

Previously researched routes are [SAMM/Farnell for Kingstate](https://farnell.samm.com/kingstate-kecg2740pbj-1299885-microphone-miniature-electret-SF) and [DigiKey for the PUI board](https://www.digikey.com/en/products/detail/pui-audio-inc/DMM-4026-B-I2S-EB-R/12315316), with [EKOM listed as Turkish DigiKey reseller](https://www.digikey.com/en/resources/authorized-digikey-reseller/turkey-ekom). This closeout does not confirm current stock, delivery dates, supplier responses or orders. Ozan must recheck exact codes and delivery before purchase.

## Results

- Comparison candidate identities are documented in [DW03-01 and DW03-02](../../decisions.md).
- Four phantom items have concrete proposals and remain OPEN.
- **NOT YET MEASURED:** microphone frequency response, lower -3 dB point, in-band noise, gain, clipping margin, phantom transfer response and placement repeatability.
- No physical validation, final sensor winner, completed purchase or passed project gate is claimed.

## Open Decisions / Risks

1. Both candidates lack explicit lower -3 dB evidence in the reviewed datasheets. Candidate selection does not waive this pre-order requirement.
2. Resolve PUI sensitivity-reference and clock-documentation ambiguities; agree the actual interface with Ozan.
3. Define the ECM bias/AFE/ADC path and check every coupling/high-pass stage against the required band.
4. Resolve DW03-04 through DW03-07 with part specifications and a buildable fixture. Exciter/fixture response could dominate the comparison.
5. Check department stock and current lead times. DW03-11 purchase readiness remains OPEN. No decisions belonging to Modules B/C are closed here.

## Next Week Handoff

Week 4 is acquisition requirements freeze and Group-A technical approval for ordering. The following work is planned; thresholds are not yet agreed or measured.

| Requirement | Kaan's Week-4 action / verification approach | Dependency / output |
|---|---|---|
| Bandwidth | Use the project's 20-500 Hz evaluation band, protecting the low-frequency region. Define tolerances/cutoffs and plan electrical AFE sweeps separately from complete phantom sweeps. | Resolve LF evidence and agree measurable acceptance criteria. |
| Gain | Define input/reference conditions, bias and ADC limits; calculate gain range and plan known electrical-input checks. | Ozan confirms ADC/interface and full scale. No universal heart-sound voltage is assumed. |
| Noise floor | Plan appropriate input termination for the analogue front end and quiet-phantom recordings of each complete chain. Specify bandwidth, gain, supply, sample format and units; compute RMS/PSD by script from retained raw data. | Separate electronics noise from microphone/ambient/mechanical noise. A digital microphone has no equivalent shorted acoustic input. |
| Clipping margin | Define maximum test stimulus and numerical headroom relative to analogue rails/ADC full scale and digital full scale. Plan an amplitude sweep and clipping-count analysis. | Agree scaling and thresholds with B/C. |
| Transducer/coupling | Freeze mounting, port clearance, coupling thickness/material, clamp method, position and cable restraint. Define controlled reseating. | Complete phantom specifications and mechanical metadata. |
| Group-A approval | Check department stock first, then exact codes, compatibility, quantities/spares and LF evidence. Review Ozan's current BOM/lead times before approving each Module A item. | Candidate selection is not blanket purchase approval. |

Items still requiring purchase-ready specification or stock confirmation include the exciter, amplifier module, silicone sample, acrylic frame/chestpiece clamp, and ECM AFE/ADC components and connection hardware. Microphone orders remain subject to the evidence/interface conditions above.
