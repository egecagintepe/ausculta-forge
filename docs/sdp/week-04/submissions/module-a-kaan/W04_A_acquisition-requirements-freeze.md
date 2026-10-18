# W04 Module A: Acquisition Requirements Freeze

**Week:** 4  
**Module:** A - Acquisition Hardware and Characterisation  
**Owner:** Kaan (`kaan0443-crypto`)  
**Updated:** 2026-10-19  
**Status:** DOCUMENTED FOR REVIEW - full requirements freeze and physical verification remain OPEN.

This is a student project with no diagnostic claim. Physical validation is restricted to an acoustic phantom. No human recordings or experimental performance results are reported. **NOT YET MEASURED.**

## Objective

The advisor's exact Week 4 Module A task was addressed: specify **gain, bandwidth, noise floor and clipping margin**. The 17 October coordination brief was also addressed through the INMP441 main path, ECM comparison dependencies, initial phantom specification and Week 5 handoff. Document preparation is complete for review; it does not establish that all acceptance limits, hardware tests or shared interfaces are closed.

## Inputs / Dependencies

- Advisor sources: `SDP4_Digital_Stethoscope_Plan_TR-1.docx`, `SDP_Assessment_Criteria_for_Students.docx`, and `SDP4_Component_Requirements_EN.docx`; references [1]-[3] in the attached report.
- Module A coordination brief, 17 October 2026; purchase information and Kaan's 19 October clarification; report reference [4].
- [Week 3 Module A submission](../../../week-03/submissions/module-a-kaan/W03_A_transducer-candidate-selection.md) and the archived candidate-selection report. Week 2 and Week 3 records were retained unchanged.
- Current [Module B requirements](../module-b-ozan/W04_B_embedded-requirements-freeze.md), [decision register](../../decisions.md), [procurement closeout](../../procurement-closeout.md), and [order ledger](../../W04_B_actual-orders_2026-10-16_v01.csv) were reviewed on 19 October.
- Manufacturer sources and their reference conditions are listed in report references [5]-[8]. Manufacturer values are not measurements of the purchased breakout boards.

### Procurement change and reported parts

The **PUI DMM-4026-B-I2S-R microphone with DMM-4026-B-I2S-EB-R evaluation board selected in Week 3 could not be obtained within the required timeframe because of supplier lead time. INMP441 modules were therefore purchased instead.** This reason was confirmed by Kaan on 19 October. INMP441 is the current main integration path; Kingstate remains the analogue comparison candidate. This is a procurement/architecture decision, not a measured final-sensor selection.

The supplied coordination record lists 3 INMP441 modules, 2 Kingstate KECG2740PBJ capsules, 5 MCP6022 op-amps, 2 exciters (30 mm / 12 ohm), 4 PAM8403 modules and prototyping items, ordered on 16 October. Purchase/order status does not establish delivery, inspection or successful operation. Public-safe supplier reconciliation remains in Module B's procurement records; no receipts or personal information are included here.

### Current A/B interface cross-check

The PDF's 48 kHz / 3.072 MHz / 3.3 V proposal agrees with the nominal acquisition profile now documented by Module B. Module B identifies the purchased board as the seller-listed **ESP32-S3-WROOM-1-N16R8**, not the earlier DevKitC-1/N8R8 candidate. GPIO4/5/6 for BCLK/WS/SD and L/R grounded for left-channel capture remain **proposals pending actual board/module inspection**. This submission does not approve their wiring or freeze USB routing, class, CRC or B/C framing. Board revision/connector mapping and physical clock/capture evidence remain open under DW04-01 through DW04-07. This live repository cross-check supplements the PDF's older REV01 reference without altering the approved PDF.

## Work Performed

The advisor's Week 4 row and coordination requirements were mapped to a requirements table. Manufacturer specifications were reviewed; the PUI-to-INMP441 change and low-frequency risk were documented. Gain selection, noise and clipping procedures were defined. An initial dimensioned phantom proposal, missing-parts list and Week 5 sequence were prepared. No new analogue circuit, phantom assembly, firmware capture or physical measurement is claimed.

### Acquisition requirements

| ID | Requirement / proposed target | Verification and remaining boundary |
|---|---|---|
| A4-01 Bandwidth | Retain the 20-500 Hz investigation band; explicitly test 20, 30, 40, 50, 60, 80, 100, 150, 200, 300 and 500 Hz; preserve unfiltered acquisition. | Record drive/reference conditions and response relative to 100 Hz. Acceptable loss/ripple, especially 20-60 Hz, remains OPEN. |
| A4-02 Gain | INMP441 raw software scaling = 1 (0 dB); no AGC or normalization in the raw record. ECM gain shall be selected against input envelope, offsets, op-amp swing and ADC range. | Verify signed decoding and electrically measure ECM Vout/Vin. Exact ECM gain depends on the still-open ADC/reference choice. |
| A4-03 Noise floor | Three 30 s baseline recordings per condition; unweighted RMS/PSD in 20-500 Hz, with separate 20-60 and 60-500 Hz results. | Preserve raw files and processing settings. Minimum useful signal and absolute noise/SNR acceptance thresholds remain OPEN. |
| A4-04 Clipping margin | PROPOSED minimum 6 dB peak headroom at the declared maximum normal phantom drive; zero saturated samples in normal tests. | Measure raw peak, rail count and compression/harmonics. The 6 dB target and maximum normal drive require acceptance; overload tests are separate. |
| A4-05 Dynamic range | Report measured band-limited noise to the highest accepted clean output under fixed settings. | Distortion acceptance limit remains OPEN. A 24-bit word is not measured dynamic range. |
| A4-06 Repeatability | Keep source, drive, fixture, contact load and cable placement fixed; initially three independent remounts. | Preserve every run; extend to the advisor's at-least-ten-repeat Week 11 campaign. |

INMP441's typical **acoustic lower -3 dB point is 60 Hz**. Its distinct internal digital high-pass corner of 3.7 Hz at 48 kHz does not remove that acoustic limitation. Loss in 20-60 Hz can affect S1/S2 energy, waveform shape and quality metrics. A first-order 60 Hz high-pass calculation was included only as an illustration, not a fitted device model or measured response. Purchase does not prove 20-500 Hz suitability.

The main INMP441 path includes its ADC and I2S output, so an external microphone AFE/ADC is not required for that path. Nominal 3.3 V, local decoupling, verified module pin labels, an unobstructed bottom port, a defined cavity/gasket and PCB support are required. I2S uses 24-bit two's-complement samples and 64 bit clocks per WS frame; capture alignment and sign extension must be verified with Module B. A 32-bit transport container is not 32-bit sensor resolution.

### ECM comparison and measurement definitions

The Kingstate path remains **capsule -> bias -> MCP6022 conditioning -> anti-alias/ADC interface -> digitizer -> recorded samples**. MCP6022 is an op-amp, not an ADC. The exact gain, supply/reference, coupling poles and ADC remain joint A/B/advisor decisions (DW04-08). The listed Kingstate 20 Hz range does not establish a documented lower -3 dB point.

- Compare both sensors using the same fixture, source, drive, contact load and remount procedure. Record unavoidable adapter/cavity differences.
- For the digital path, exciter-off records with amplifier powered-silent and powered-off measure the **quiet-condition system floor**, including ambient/mechanical noise; they do not isolate microphone self-noise.
- For ECM electronics, disconnect the capsule and terminate the signal input at its correct AC reference while preserving DC bias; compare shorted-input, representative source-impedance and capsule-installed conditions. Never short power rails or I2S outputs.
- Decode INMP441 samples before using `x = sample / 2^23`. Peak dBFS is `20*log10(max(abs(x)))`; the report explicitly references RMS dBFS to a full-scale sine. Proposed 6 dB headroom corresponds to peak fraction approximately 0.501. Inspect compression/harmonics as well as digital rail counts.
- Absolute SPL/equivalent-input noise requires independent acoustic calibration. Constant electrical drive does not imply constant acoustic pressure; without a characterized reference, report the complete phantom/sensor path rather than an isolated sensor response.

### Initial phantom specification

- **Exciter/amplifier:** reported 30 mm / 12 ohm exciter with PAM8403. PAM8403 drives the phantom and is not the microphone AFE. Exact exciter power rating and amplifier module schematic/input capacitors remain unverified. Start with a regulated current-limited supply and low drive; increase only within verified ratings.
- **Bridge-output safety:** connect one exciter across one channel's + and - outputs. Neither output is ground; do not parallel channels or attach an earth-referenced scope clip to a switched output. Use appropriate differential measurement and account for PWM when measuring audio RMS.
- **Band test:** stepped tones at A4-01 frequencies, initially at least 1 s settling then 5 s per tone, three repeats. Record generator/DAC level, loaded drive voltage and reference conditions. This is a planned test, not a result.
- **Coupling:** proposed nominal 3 mm dry silicone, starting 60 x 60 mm coupon; record material, thickness, hardness if available and compression. Gel remains a later alternative and must not enter the port.
- **Frame:** proposed 200 x 150 x 6 mm plywood base, 160 x 30 x 10 mm bridge, nominal 80 mm standoffs, 60 x 60 x 2 mm perimeter-supported acrylic drive plate and at least 20 mm clamp travel. See PDF page 6 for the sketch. Final joints, hole/bridge arrangement and real-part fit require detailing before fabrication.
- **Contact/mount:** proposed initial 1 N normal force, checked by a force gauge or calibrated balance arrangement; measure area before reporting pressure. Use physical stops, interchangeable adapters, a defined cavity/gasket and cable strain relief. These dimensions/load are starting proposals, not measured optima.
- **Still to verify/source:** silicone, frame/plate material, gasket, chestpiece/adapters, clamp, fasteners, cable restraint, force-measurement access, regulated supply, generator, oscilloscope/differential measurement, multimeter, soldering access and a suitable DAC/analogue playback output/cables. Check inventory before additional purchases. PAM8403 does not accept I2S directly.

## Evidence

1. [English technical report, revision 1.1, 19 October 2026](W04_A_acquisition-requirements-report_v01.pdf), 8 pages. Repository file version `v01` is the first Week 4 upload; the document's internal revision is 1.1.
2. PDF SHA-256: `1dcb630340a9eac87c4c870353297b5d95b8b3c4bfe8d8868f12056e230e1410`.
3. [Reproducible illustrative calculation script](W04_A_requirements-calculations_v01.py) and [generated illustration CSV](W04_A_illustrative-highpass_v01.csv). Run `python W04_A_requirements-calculations_v01.py` in this folder; only Python standard-library modules are required. The script regenerates the CSV and prints clock/headroom calculations. **No experimental data are generated.**
4. Datasheet references [5]-[8] and advisor/coordination references [1]-[4] are listed in the PDF. The approved PDF was uploaded unchanged.

The PDF pages were visually checked; the calculation output was reproduced and local file links/hash were checked. Runtime or hardware tests were not run for this documentation submission.

## Results

- The four requested Week 4 acquisition topics and the coordination brief were documented with verification methods.
- The supplier-lead-time reason for the INMP441 replacement was recorded; Kingstate was retained for comparison.
- Requirements, manufacturer facts, proposed targets and unmeasured performance were explicitly separated.
- An initial phantom specification and Week 5 preparation sequence were prepared.
- **Physical gain, frequency response, noise floor, clipping, dynamic range, repeatability and G1: NOT YET MEASURED / NOT RUN.** Full requirements freeze and advisor acceptance remain pending.

## Open Decisions / Risks

| Topic | Required closure / owner |
|---|---|
| INMP441 low-frequency suitability (DW04-02) | Kaan + advisor: acceptable 20-60 Hz loss/band tolerance, followed by mounted phantom evidence. |
| Noise/dynamic range/headroom | Kaan + advisor: minimum useful signal, noise/SNR and distortion limits, maximum normal stimulus, acceptance of the proposed 6 dB margin. |
| Board and I2S integration (DW04-01/03) | Ozan + Kaan: actual PCB/module pin labels, verified wiring, clock measurements, slot decoding and raw-data handling. |
| ECM path (DW04-08) | Kaan + Ozan + advisor: ADC, reference/input range, gain and conditioning design; internal ADC1 and PCM1808-class external ADC remain candidates only. |
| Phantom | Kaan: exact exciter ratings, amplifier board components, mechanical fit/detailing, coupling and controlled contact load; lab/inventory checks. |
| B/C protocol and shared G1 (DW04-05/06/07/10) | Ozan + Ege retain ownership; no USB class, CRC, final frame format or G1 completion is unilaterally closed here. |

No shared decision row is marked CLOSED by this submission. Procurement and technical suitability are distinct.

## Next Week Handoff

For Week 5 (19-25 October), prepare the fixture drawing/detailing, run-log fields, analysis environment and lab access before delivery. On receipt, record non-sensitive part/board identity, inspect ports/pins and verify supplies before wiring. Coordinate safe I2S connection and first raw capture with Ozan. Assemble the mechanical fixture and check PAM8403/exciter at low drive; record noise/controlled tones when the acquisition path is ready.

The advisor's **Week 5 breadboard front-end and shorted-input noise-floor task remains in scope**. The digital microphone has no accessible analogue signal input to short. The ECM branch can fulfil the original task; deferral or substitution requires a documented advisor-approved change. No cancellation is implied by the digital main path.

Ozan and Ege own the physical MCU-to-PC synthetic G1 integration. Module A can prepare mechanics, electrical safety checks and procedures independently; standalone digitizer tests require a suitable available instrument. Kaan supplies acquisition conditions and hardware status. Each later physical run must retain raw files, configuration, source/firmware/script versions, gain, supply, stimulus, coupling thickness, contact load, environment and result status; the final shared metadata schema remains with Module C.
